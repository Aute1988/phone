# -*- mode: python ; coding: utf-8 -*-
# ============================================================================
# PyInstaller spec 文件 - 手机号去重工具（仅 Windows）
#
# 构建命令：
#   python -m PyInstaller phone_dedup.spec
#
# 【重要】
#  - 本项目只做 Windows 版本
#  - 目标系统：Windows 10 (1809+) 及以上
#  - 构建产物：单文件夹绿色版（dist/phone_dedup_tool/）
#  - 客户解压到任意目录，双击 start.bat 即可使用
#
# 【为什么用 INTERNAL_NAME 而不是中文】
#  - PyInstaller 的 EXE/COLLECT 不支持中文路径，会导致 Windows 报错
#  - 内部统一英文名，外部用 start.bat 包装中文显示
# ============================================================================

import sys
from pathlib import Path

block_cipher = None

ROOT = Path(SPECPATH).resolve()
MAIN_SCRIPT = ROOT / "server.py"
FRONTEND = ROOT / "index.html"

# 内部统一用英文名（避免 Windows 中文路径问题）
INTERNAL_NAME = "phone_dedup_tool"

# --------------------------------------------------------------------------
# Analysis：扫描 server.py 及其依赖
# --------------------------------------------------------------------------
a = Analysis(
    [str(MAIN_SCRIPT)],
    pathex=[],
    binaries=[],
    datas=[
        # index.html 打包进 app（运行时从 _MEIPASS 读取）
        (str(FRONTEND), "."),
    ],
    hiddenimports=[
        # ────── uvicorn 动态加载 ──────
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.auto",
        "uvicorn.server",

        # ────── starlette / fastapi ──────
        "starlette",
        "starlette.routing",
        "starlette.responses",
        "starlette.middleware",
        "starlette.middleware.cors",
        "starlette.testclient",
        "starlette.concurrency",
        "starlette.background",
        "starlette.requests",
        "starlette.staticfiles",
        "starlette.datastructures",
        "starlette.exceptions",
        "starlette.formparsers",
        "starlette.status",
        "starlette.types",
        "starlette.applications",
        "fastapi",
        "fastapi.responses",
        "fastapi.staticfiles",
        "fastapi.params",
        "fastapi.middleware",
        "fastapi.utils",

        # ────── pydantic v2 子模块（CI 用的是 pydantic 2.x） ──────
        "pydantic",
        "pydantic._internal",
        "pydantic._internal._generate_schema",
        "pydantic._internal._validators",
        "pydantic._internal._fields",
        "pydantic._internal._typing_extra",
        "pydantic._internal._config",
        "pydantic.functional_validators",
        "pydantic.functional_serializers",
        "pydantic.json_schema",
        "pydantic.errors",
        "pydantic.warnings",
        "pydantic.fields",
        "pydantic.types",
        "pydantic.networks",
        "pydantic.deprecated",
        "pydantic.deprecated.class_validators",
        "pydantic.validate_call_decorator",
        "annotated_types",
        "typing_extensions",

        # ────── pandas 2.x 子模块 ──────
        "pandas",
        "pandas._libs",
        "pandas._libs.window",
        "pandas._libs.tslibs",
        "pandas._libs.hashtable",
        "pandas._libs.lib",
        "pandas._libs.arrays",
        "pandas._libs.sparsing",
        "pandas._libs.index",
        "pandas._libs.interval",
        "pandas._libs.join",
        "pandas._libs.missing",
        "pandas._libs.ops",
        "pandas._libs.parsers",
        "pandas._libs.properties",
        "pandas._libs.reduction",
        "pandas._libs.reshape",
        "pandas._libs.skiplist",
        "pandas._libs.sorting",
        "pandas._libs.testing",
        "pandas._libs.tslib",
        "pandas._libs.writers",
        "pandas._config",
        "pandas.io",
        "pandas.io.excel",
        "pandas.io.formats",
        "pandas.io.common",
        "pandas.io.parsers",
        "pandas.errors",
        "pandas.core",
        "pandas.core.arrays",
        "pandas.core.dtypes",
        "pandas.core.indexes",
        "pandas.core.ops",
        "pandas.core.reshape",
        "pandas.core.series",
        "pandas.core.frame",
        "pandas.util",
        "pandas.util._decorators",
        "pandas.util._tester",
        "pandas.util._validators",
        "dateutil",
        "dateutil.parser",
        "dateutil.relativedelta",
        "dateutil.rrule",
        "pytz",
        "numpy",
        "numpy.core",
        "numpy._core",

        # ────── openpyxl ──────
        "openpyxl",
        "openpyxl.cell",
        "openpyxl.cell._writer",
        "openpyxl.workbook",
        "openpyxl.worksheet",
        "openpyxl.utils",
        "openpyxl.styles",
        "openpyxl.formatting",
        "openpyxl._constants",
        "openpyxl.reader",
        "openpyxl.writer",
        "openpyxl.descriptors",
        "openpyxl.descriptors.serialisable",
        "et_xmlfile",
        "et_xmlfile.incremental_tree",

        # ────── 文件上传 ──────
        "python_multipart",
        "multipart",
        "multipart.multipart",
        "multipart.py3",

        # ────── xlrd（xls 格式支持，可选） ──────
        "xlrd",
    ],
    hookspath=[],
    hooksconfig={},
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# --------------------------------------------------------------------------
# PYZ：压缩所有 Python 字节码
# --------------------------------------------------------------------------
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=INTERNAL_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                       # 关闭 UPX：避免在没装 UPX 的环境静默失败
    console=True,                    # Windows 显示控制台（便于查看日志）
    disable_windowed_traceback=False,
)

# --------------------------------------------------------------------------
# COLLECT：合并 exe + 运行时依赖 → 输出单文件夹绿色版
# --------------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=INTERNAL_NAME,
)
