# 📱 手机号去重管理工具

一个**完全本地运行**的桌面工具，用于批量上传手机号文件、自动去重、并下载不重复的部分。

> 数据存在你自己电脑上的 SQLite 文件里，**不上传任何服务器**，100% 隐私安全。

---

## ✨ 能做什么？

| 功能 | 说明 |
|---|---|
| 📤 上传文件 | 支持 `.txt` / `.xlsx` / `.xls` / `.csv` 格式，每批约 1 万条 |
| 🔍 自动去重 | 跟历史库对比，自动算出哪些是重复的、哪些是新增的 |
| 📥 立刻下载 | 上传完顶部弹出横幅，**一眼看到结果、一键下载不重复的部分**（TXT 或 Excel） |
| 🔎 搜索手机号 | 在历史库中精确/模糊搜索，支持分页加载 |
| 📦 导出全库 | 一键导出整个数据库的全部手机号（TXT 或 Excel） |
| 📚 历史记录 | 每次上传都记下来，每行都能直接下载（TXT/Excel 按钮） |

---

## 🚀 怎么用？

### Mac（开发模式）

```bash
# 第一次：配置环境（只需跑一次，约 3-5 分钟）
cd ~/Desktop/手机号
bash setup_mac.sh

# 之后：每次启动
python3 server.py
```

启动后浏览器会自动打开 `http://localhost:8765`。

### Windows（开发模式）

双击 `start.bat`，浏览器会自动打开 `http://localhost:8765`。

---

## 📖 操作步骤

1. **打开页面** → http://localhost:8765
2. **上传文件** → 把 txt/excel 拖进虚线框（或点击虚线框选文件）
3. **看结果** → 页面顶部弹出绿色横幅，显示"上传 X 条 / 新增 X 条 / 重复 X 条"
4. **下载不重复的部分** → 点横幅里的「⬇️ 下载本次不重复」按钮

---

## 🎁 打包 EXE 给客户

打包后客户**不需要装 Python**，双击就能用。

### 在 Windows 上打包

双击 `build.bat`（或 cmd 里运行 `build.bat`），产物在 `dist\phone_dedup_tool\`。

### 分发给客户

把整个 `dist\phone_dedup_tool\` 文件夹**压缩成 zip**，发给客户：

1. 客户解压到任意目录
2. 双击 `start.bat`（**注意是 .bat，不是 .exe**）
3. 浏览器自动打开 `http://localhost:8765`，即可使用

> ⚠️ 杀毒软件误报是 PyInstaller 打包常见问题，把文件夹加信任即可。

### 打包后界面会变吗？

**不会**！打包只是把 Python 解释器和依赖打进 exe 里，**HTML/CSS/JS 全部原样保留**。

界面 = 完全一样，**只是不再依赖系统装了 Python**。

---

## 📂 客户的数据存哪里？

打包后用户的手机号库放在 Windows 标准数据目录：

```
C:\Users\<用户名>\AppData\Roaming\手机号去重工具\
├── data\
│   ├── history.db        ← 手机号库（不要删！删了数据就没了）
│   └── exports\          ← 导出的无重复版
```

启动时控制台会打印路径，方便排查。

迁移到新电脑：把整个 `手机号去重工具\` 文件夹复制过去即可。

---

## 🔧 端口冲突

默认端口 `8765`。如果被占用：

- **Mac**：启动前先设环境变量 `export PORT=8888 && python3 server.py`
- **Windows**：编辑 `start.bat` 里的 `set PORT=8765` 改成别的

---

## ❓ 常见问题

**Q: 关掉浏览器后还能用吗？**
A: 可以，关浏览器不影响服务。再访问 http://localhost:8765 即可。要彻底停止：在终端按 Ctrl+C。

**Q: 数据库在哪？怎么备份？**
A: Mac 在 `~/Library/Application Support/手机号去重工具/data/history.db`；Windows 在 `%APPDATA%\手机号去重工具\data\history.db`。整个文件复制走就是备份。

**Q: 想清空重新开始？**
A: 停止服务后，删除上面那个 `history.db` 文件即可。

**Q: 杀毒软件报警告？**
A: PyInstaller 打包的常见误报，把 `phone_dedup_tool/` 文件夹加入信任即可。

**Q: 11 位手机号怎么验证？**
A: 文件里每行一个手机号，**严格 11 位数字**（中国大陆手机号格式）。不合法的行会自动跳过，结果里会显示"跳过 N 条"。

**Q: 重复逻辑是怎样的？**
A: 数据库已有 N 条，本次上传 M 条，其中 X 条已在库里 → 这次新增 `M-X` 条，**下载的就是这 M-X 条**。

---

## 📁 项目文件结构

```
手机号/
├── server.py             # 后端服务（FastAPI）
├── index.html            # 前端页面
├── requirements.txt      # Python 依赖
├── phone_dedup.spec      # PyInstaller 打包配置
├── start.bat             # Windows 启动脚本
├── build.bat             # Windows 打包脚本
├── download_deps.bat     # Windows 离线依赖下载（可选）
├── setup_mac.sh          # Mac 环境配置脚本
├── post_install.sh       # Mac 安装后处理
├── 使用说明.txt            # 给最终客户的中文说明
├── README.md             # 本文件
└── .gitignore            # Git 忽略配置
```

---

## 🛠 技术栈

- Python 3.12（Mac）/ 3.11+（Windows）
- FastAPI 0.110 — 后端
- SQLite — 本地存储（开启 WAL 模式、缓存优化）
- pandas 2.2 — excel 解析
- openpyxl 3.1 — excel 写入（write_only 模式，百万级不爆内存）
- PyInstaller — 打包成 exe

---

## 📊 性能参考（实测）

| 条数 | 数据库大小 | 搜索耗时 | 全库导出 |
|---|---|---|---|
| 1 万 | ~300KB | < 10ms | < 100ms |
| 50 万 | ~15MB | ~100ms | ~500ms |
| 100 万 | ~30MB | ~200ms | ~1s |
