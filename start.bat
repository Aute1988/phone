@echo off
chcp 65001 >nul
REM 📱 手机号去重工具 - Windows 一键启动
REM 如果 vendor/ 目录里有本地 wheel，会优先使用（无需联网）

cd /d "%~dp0"
set PORT=8765

echo 🚀 正在启动手机号去重工具...
echo 📂 工作目录: %cd%

where python >nul 2>nul
if %errorlevel% neq 0 (
  echo ❌ 未检测到 python，请先安装 Python 3.11+
  pause & exit /b 1
)

REM 检查 Python 版本（需要 3.11+，因为 pandas 2.x 需要）
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo ✓ 检测到 Python %PY_VER%

REM 创建虚拟环境
if not exist ".venv" (
  echo 📦 首次启动，正在创建虚拟环境...
  python -m venv .venv
  if %errorlevel% neq 0 (
    echo ❌ 创建虚拟环境失败
    pause & exit /b 1
  )
)

call .venv\Scripts\activate.bat

REM 检查依赖
if not exist ".venv\.installed" (
  set PLATFORM_WHEELS=%cd%\vendor\windows-x64
  set COMMON_WHEELS=%cd%\vendor\common

  if exist "%PLATFORM_WHEELS%" if exist "%COMMON_WHEELS%" (
    if not exist "%PLATFORM_WHEELS%\*" goto :online_install
    if not exist "%COMMON_WHEELS%\*" goto :online_install

    echo 📦 使用本地 wheel 安装（无需联网）...
    pip install --quiet --disable-pip-version-check --no-index ^
      --find-links "%PLATFORM_WHEELS%" ^
      --find-links "%COMMON_WHEELS%" ^
      -r requirements.txt
    if %errorlevel% neq 0 (
      echo ⚠️ 本地 wheel 安装失败，回退到联网
      pip install --quiet --disable-pip-version-check -r requirements.txt
    )
    goto :install_done
  )

  :online_install
  echo 📦 vendor/ 不齐全，从网络安装依赖（仅首次，约 30 秒）...
  pip install --quiet --disable-pip-version-check -r requirements.txt
  if %errorlevel% neq 0 (
    echo ❌ 依赖安装失败，请检查网络
    pause & exit /b 1
  )
  echo.
  echo 💡 小提示：运行 download_deps.bat 可把依赖下载到 vendor\
  echo    之后启动无需联网，速度更快。

  :install_done
  echo. > .venv\.installed
)

REM 自动打开浏览器
start "" "http://localhost:%PORT%"

REM 启动服务
echo ✅ 启动成功！浏览器已打开 http://localhost:%PORT%
echo 💡 关闭此窗口即可停止服务
echo.
python server.py
pause
