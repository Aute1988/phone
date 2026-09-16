"""
📱 手机号去重管理工具 - 后端服务（仅 Windows）
技术栈：FastAPI + SQLite + pandas
所有数据本地存储，零网络外发。

PyInstaller 打包模式：
  - 内部资源（index.html）从 _MEIPASS 读
  - 用户数据（db / 导出文件）放在 Windows 用户专属目录：
      %APPDATA%/手机号去重工具/   (主)
      %LOCALAPPDATA%/手机号去重工具/  (备)
    （避免写入 exe 内部，绕开权限问题）
"""
import os
import re
import sys

# 【关键】PyInstaller 打包时必须最先处理，防止 print 失效
if getattr(sys, "frozen", False):
    try:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
    except Exception:
        pass

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse

# ============ PyInstaller 路径兼容 ============
if getattr(sys, "frozen", False):
    MEIPASS_DIR = Path(sys._MEIPASS)
else:
    MEIPASS_DIR = Path(__file__).parent.resolve()


def _get_user_data_dir() -> Path:
    """
    获取用户专属数据目录（Windows 优先）。

    优先级（遇到不可写就降级）：
      1) exe 同目录的 data/（PyInstaller 打包后，优先）
      2) %APPDATA%/手机号去重工具/           （Windows 标准位置）
      3) %LOCALAPPDATA%/手机号去重工具/      （Windows 本地）
      4) ~/手机号去重工具/                  （用户目录）
      5) 当前目录的 phone_dedup_data/       （兜底）
      6) 系统临时目录                        （极端兜底）

    返回值是不含 data/ 的 BASE_DIR，外面会再拼 data/exports。
    """
    app_name = "手机号去重工具"

    # ────── PyInstaller 打包后：存 exe 同目录下 ──────
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent.resolve()
        data_dir = exe_dir / "data"
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            test_file = data_dir / ".write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            return data_dir
        except (OSError, PermissionError):
            pass

    candidates = []

    # ────── Windows 标准位置（开发/非打包）──────
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(Path(appdata) / app_name)
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            candidates.append(Path(localappdata) / app_name)
        candidates.append(Path.home() / app_name)
    else:
        # 非 Windows（开发机 Mac/Linux）：用 home 下的对应位置
        candidates.append(Path.home() / app_name)

    # 兜底：当前工作目录里的 phone_dedup_data/（明确命名，不会污染 cwd）
    candidates.append(Path.cwd() / "phone_dedup_data")

    chosen = None
    is_fallback = False
    for i, path in enumerate(candidates):
        try:
            path.mkdir(parents=True, exist_ok=True)
            # 测试一下能不能写（mkdir 在沙盒里可能成功但 write 会失败）
            test_file = path / ".write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            chosen = path
            # 最后一个候选就是兜底
            is_fallback = (i == len(candidates) - 1)
            break
        except (OSError, PermissionError):
            continue

    if chosen is None:
        # 极端兜底：用 tempfile（系统临时目录，绝对能写）
        import tempfile
        chosen = Path(tempfile.gettempdir()) / app_name
        chosen.mkdir(parents=True, exist_ok=True)
        is_fallback = True

    if is_fallback:
        print(
            f"[警告] 标准数据目录不可写，已降级到: {chosen}",
            file=sys.stderr,
        )
        print(
            f"        （推荐改用标准位置：{candidates[0]}）",
            file=sys.stderr,
        )
        if "phone_dedup_data" in str(chosen):
            print(
                "        数据会存在当前目录的 phone_dedup_data/ 下",
                file=sys.stderr,
            )
        else:
            print(
                "        ⚠️ 临时目录里的数据系统重启后会丢失！",
                file=sys.stderr,
            )

    return chosen


BASE_DIR = _get_user_data_dir()
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = DATA_DIR / "exports"
# 确保 data/ 和 data/exports/ 都存在
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"[警告] 创建子目录失败: {e}", file=sys.stderr)
DB_PATH = DATA_DIR / "history.db"
INDEX_HTML = MEIPASS_DIR / "index.html"
PORT = int(os.environ.get("PORT", "8765"))

# 文件大小上限：50MB（前端也会校验，但后端必须独立校验防止绕过）
MAX_FILE_SIZE = 50 * 1024 * 1024

# 严格 11 位数字校验（中国大陆手机号）
# 1 开头，第二位 3-9（覆盖 130-199 全段）
PHONE_RE = re.compile(r"^1[3-9]\d{9}$")

# ============ 数据库 ============
def get_conn() -> sqlite3.Connection:
    """获取数据库连接，开启 WAL + 性能 PRAGMA"""
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-65536")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=268435456")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """初始化表结构 + 索引"""
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS phones (
            phone_number TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS upload_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            upload_time TEXT NOT NULL,
            total_count INTEGER NOT NULL,
            duplicate_count INTEGER NOT NULL,
            new_count INTEGER NOT NULL,
            skipped_count INTEGER NOT NULL DEFAULT 0,
            export_filename TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_upload_time
            ON upload_records(upload_time DESC);

        CREATE INDEX IF NOT EXISTS idx_filename
            ON upload_records(filename);
        """
    )
    conn.execute("ANALYZE")
    conn.close()


init_db()

# ============ FastAPI 应用 ============
app = FastAPI(title="手机号去重工具", version="1.0")


def _extract_phones_from_df(df: pd.DataFrame) -> tuple[List[str], int, int]:
    """
    从 DataFrame 抽取手机号。
    返回: (valid_phones, total_valid_rows, raw_count)

    - valid_phones: 去重后的有效手机号列表
    - total_valid_rows: 文件中"看起来是手机号"的行总数（含重复）
    - raw_count: DataFrame 总行数
    """
    candidates = set()
    total_valid_rows = 0
    raw_count = len(df)
    for col in df.columns:
        series = df[col].astype(str).str.strip()
        for v in series:
            if v and PHONE_RE.match(v):
                candidates.add(v)
                total_valid_rows += 1
    return list(candidates), total_valid_rows, raw_count


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    上传手机号文件：
    1. 解析（txt / xlsx / xls / csv）
    2. 校验 11 位
    3. 与历史库对比，算出重复 / 新增
    4. 新增的入库
    5. 导出"无重复版.txt"
    6. 记录本次上传元信息
    """
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "文件为空")
    # 【安全】后端独立校验文件大小，防止绕过前端限制
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(413, f"文件过大（>{MAX_FILE_SIZE // 1024 // 1024}MB），请检查")

    # 【安全】只取 basename，防止路径穿越
    raw_filename = file.filename or "未命名.txt"
    safe_filename = Path(raw_filename).name
    if not safe_filename:
        safe_filename = "未命名.txt"
    name_without_ext = Path(safe_filename).stem or "未命名"
    suffix = Path(safe_filename).suffix.lower()

    # ---- 1. 解析 ----
    try:
        import io
        if suffix in (".xlsx", ".xls"):
            try:
                engine = "openpyxl" if suffix == ".xlsx" else "xlrd"
                df = pd.read_excel(io.BytesIO(raw), dtype=str, header=None, engine=engine)
            except ImportError:
                raise HTTPException(
                    400,
                    f"读取 .{suffix} 需要额外依赖。请把文件另存为 .xlsx 再上传"
                )
            except Exception as e:
                raise HTTPException(400, f"Excel 解析失败：{e}")
        elif suffix == ".csv":
            # 处理 BOM：Excel 导出的中文 CSV 常带 UTF-8 BOM
            if raw[:3] == b"\xef\xbb\xbf":
                raw = raw[3:]
            # 尝试多种中文编码
            text = None
            for enc in ("utf-8", "gbk", "gb18030", "big5"):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if text is None:
                # 兜底：latin1 永远能解码，但可能有乱码
                text = raw.decode("latin1", errors="ignore")
            df = pd.read_csv(io.StringIO(text), dtype=str, header=None, keep_default_na=False)
        else:
            # txt
            text = raw.decode("utf-8", errors="ignore")
            if text.startswith("\ufeff"):
                text = text[1:]
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if not lines:
                raise HTTPException(400, "文件没有可解析内容")
            sample = lines[:5]
            if any("," in ln for ln in sample):
                rows = [ln.split(",") for ln in lines]
            elif any("\t" in ln for ln in sample):
                rows = [ln.split("\t") for ln in lines]
            else:
                rows = [[ln] for ln in lines]
            df = pd.DataFrame(rows)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"解析失败：{e}")

    # ---- 2. 抽取 & 校验 ----
    valid_phones, total_valid_rows, raw_count = _extract_phones_from_df(df)
    if not valid_phones:
        raise HTTPException(400, "没有找到任何有效的 11 位手机号")

    # skipped = 文件内重复 + 完全无效的行
    dup_in_file = max(0, total_valid_rows - len(valid_phones))
    invalid = max(0, raw_count - total_valid_rows)
    skipped = dup_in_file + invalid

    # ---- 3. 对比历史库 ----
    conn = get_conn()
    try:
        new_phones = []
        existing_set = set()
        BATCH = 500
        for i in range(0, len(valid_phones), BATCH):
            chunk = valid_phones[i:i + BATCH]
            placeholders = ",".join("?" * len(chunk))
            existing_rows = conn.execute(
                f"SELECT phone_number FROM phones WHERE phone_number IN ({placeholders})",
                chunk,
            ).fetchall()
            chunk_existing = {r["phone_number"] for r in existing_rows}
            existing_set.update(chunk_existing)
            new_phones.extend([p for p in chunk if p not in chunk_existing])
        duplicate_count = len(valid_phones) - len(new_phones)

        # ---- 4. 新增的入库 ----
        if new_phones:
            conn.executemany(
                "INSERT OR IGNORE INTO phones(phone_number) VALUES (?)",
                [(p,) for p in new_phones],
            )

        # ---- 5. 导出"无重复版" ----
        # 【安全】用 record id 加后缀避免冲突，覆盖前也允许
        timestamp_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"{name_without_ext}_无重复版_{timestamp_suffix}.txt"
        export_path = EXPORTS_DIR / export_filename
        with open(export_path, "w", encoding="utf-8") as f:
            for p in new_phones:
                f.write(p + "\n")

        # ---- 6. 写上传记录 ----
        upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.execute(
            """
            INSERT INTO upload_records
                (filename, upload_time, total_count, duplicate_count, new_count, skipped_count, export_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                safe_filename,
                upload_time,
                len(valid_phones),
                duplicate_count,
                len(new_phones),
                skipped,
                export_filename,
            ),
        )
        record_id = cur.lastrowid
    finally:
        conn.close()

    return {
        "ok": True,
        "record_id": record_id,
        "filename": safe_filename,
        "total_count": len(valid_phones),
        "duplicate_count": duplicate_count,
        "new_count": len(new_phones),
        "skipped_count": skipped,
        "export_filename": export_filename,
        "upload_time": upload_time,
    }


@app.get("/api/records")
def list_records():
    """列出所有历史上传记录（最新的在前）"""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, filename, upload_time, total_count, duplicate_count,
               new_count, skipped_count, export_filename
        FROM upload_records
        ORDER BY id DESC
        """
    ).fetchall()
    conn.close()
    return {"records": [dict(r) for r in rows]}


@app.get("/api/stats")
def stats():
    """首页统计：总手机号数 / 总上传次数"""
    conn = get_conn()
    total_phones = conn.execute("SELECT COUNT(*) AS c FROM phones").fetchone()["c"]
    total_uploads = conn.execute("SELECT COUNT(*) AS c FROM upload_records").fetchone()["c"]
    conn.close()
    return {"total_phones": total_phones, "total_uploads": total_uploads}


@app.get("/api/download/{record_id}")
def download(record_id: int, format: str = "txt"):
    """下载某次上传的无重复版。format: txt | xlsx"""
    if record_id <= 0:
        raise HTTPException(400, "无效的 record_id")

    conn = get_conn()
    row = conn.execute(
        "SELECT export_filename, upload_time FROM upload_records WHERE id = ?",
        (record_id,),
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(404, "记录不存在")

    # 【安全】强制只取 basename，禁止任何路径成分
    safe_export_name = Path(row["export_filename"]).name
    if not safe_export_name or safe_export_name != row["export_filename"]:
        raise HTTPException(400, "非法的文件路径")
    txt_path = EXPORTS_DIR / safe_export_name
    # 【安全】确保文件在 EXPORTS_DIR 内（防 symlink 攻击）
    try:
        if not str(txt_path.resolve()).startswith(str(EXPORTS_DIR.resolve())):
            raise HTTPException(400, "非法的文件路径")
    except (OSError, RuntimeError):
        raise HTTPException(400, "非法的文件路径")
    if not txt_path.exists():
        raise HTTPException(404, "导出文件已丢失，请重新上传")

    if format == "txt":
        return FileResponse(
            path=txt_path,
            media_type="text/plain; charset=utf-8",
            filename=safe_export_name,
        )

    if format == "xlsx":
        import io
        from openpyxl import Workbook
        wb = Workbook(write_only=True)
        ws = wb.create_sheet("无重复手机号")
        ws.append(["phone_number"])
        with open(txt_path, "r", encoding="utf-8") as f:
            for ln in f:
                p = ln.strip()
                if p:
                    ws.append([p])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        xlsx_name = Path(safe_export_name).with_suffix(".xlsx").name
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{xlsx_name}"'},
        )

    raise HTTPException(400, "format 必须是 txt 或 xlsx")


# ============ 搜索手机号 ============
@app.get("/api/search")
def search_phones(q: str = "", limit: int = 100, offset: int = 0):
    """搜索手机号"""
    q = (q or "").strip()
    if not q:
        return {"total": 0, "results": [], "exact_match": False}

    q_clean = re.sub(r"\D", "", q)
    if not q_clean:
        return {"total": 0, "results": [], "exact_match": False}

    # 至少 2 位才允许搜索（避免单字符全表扫）
    if len(q_clean) < 2:
        return {"total": 0, "results": [], "exact_match": False, "error": "至少输入 2 位数字"}

    limit = min(max(1, limit), 1000)
    offset = max(0, offset)

    conn = get_conn()
    try:
        exact_match = False
        if len(q_clean) == 11:
            row = conn.execute(
                "SELECT phone_number FROM phones WHERE phone_number = ?", (q_clean,)
            ).fetchone()
            exact_match = row is not None

        like_contain = "%" + q_clean + "%"

        total_row = conn.execute(
            "SELECT COUNT(*) AS c FROM phones WHERE phone_number LIKE ?", (like_contain,)
        ).fetchone()
        total = total_row["c"]

        rows = conn.execute(
            "SELECT phone_number FROM phones WHERE phone_number LIKE ? ORDER BY phone_number LIMIT ? OFFSET ?",
            (like_contain, limit, offset),
        ).fetchall()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "exact_match": exact_match,
            "results": [r["phone_number"] for r in rows],
        }
    finally:
        conn.close()


# ============ 导出整个数据库 ============
@app.get("/api/export-all")
def export_all(format: str = "txt"):
    """导出整个数据库。format: txt | xlsx"""
    conn = get_conn()
    try:
        total_row = conn.execute("SELECT COUNT(*) AS c FROM phones").fetchone()
        total = total_row["c"]
        if total == 0:
            raise HTTPException(400, "数据库为空，无可导出内容")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "txt":
            filename = f"全部手机号_{timestamp}.txt"

            def iter_txt():
                # 【修复】用 with 上下文确保连接一定关闭
                with get_conn() as conn2:
                    cur = conn2.execute("SELECT phone_number FROM phones ORDER BY phone_number")
                    while True:
                        rows = cur.fetchmany(5000)
                        if not rows:
                            break
                        yield ("\n".join(r["phone_number"] for r in rows) + "\n").encode("utf-8")

            return StreamingResponse(
                iter_txt(),
                media_type="text/plain; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

        if format == "xlsx":
            import io
            from openpyxl import Workbook
            filename = f"全部手机号_{timestamp}.xlsx"

            wb = Workbook(write_only=True)
            ws = wb.create_sheet("全部手机号")
            ws.append(["phone_number"])
            # 【修复】用 with 上下文管理游标
            with conn.execute("SELECT phone_number FROM phones ORDER BY phone_number") as cur:
                while True:
                    rows = cur.fetchmany(5000)
                    if not rows:
                        break
                    for r in rows:
                        ws.append([r["phone_number"]])
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            return Response(
                content=buf.getvalue(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

        raise HTTPException(400, "format 必须是 txt 或 xlsx")
    finally:
        conn.close()


# ============ 数据目录信息 ============
@app.get("/api/info")
def info():
    """返回数据目录等信息，方便排查"""
    try:
        db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    except OSError:
        db_size = 0
    return {
        "data_dir": str(DATA_DIR),
        "db_path": str(DB_PATH),
        "db_size_bytes": db_size,
        "exports_dir": str(EXPORTS_DIR),
        "frozen": getattr(sys, "frozen", False),
        "platform": sys.platform,
    }


# ============ 静态前端 ============
@app.get("/", response_class=HTMLResponse)
def index():
    """首页直接返回 index.html"""
    if INDEX_HTML.exists():
        return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>请先创建 index.html</h1>")


# 注：删除了 StaticFiles 挂载（避免泄露 _MEIPASS 内所有文件）


# ============ 启动入口 ============
if __name__ == "__main__":
    import uvicorn
    from multiprocessing import freeze_support
    freeze_support()

    print(f"\n{'=' * 60}")
    print(f"🚀 手机号去重工具 已启动")
    print(f"🌐 访问地址: http://localhost:{PORT}")
    print(f"💾 数据目录: {DATA_DIR}")
    print(f"{'=' * 60}\n")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="info")
