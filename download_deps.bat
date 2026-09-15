@echo off
REM ============================================================================
REM 📥 依赖本地化脚本 (Windows) - 把所有 Python 包下载到本地 vendor/ 目录
REM
REM 使用方法：双击或 download_deps.bat
REM ============================================================================
chcp 65001 >nul

cd /d "%~dp0"

set VENDOR_DIR=vendor
set COMMON_DIR=%VENDOR_DIR%\common
set PLATFORM_DIR=%VENDOR_DIR%\windows-x64

echo ============================================================
echo   📥 下载依赖到本地 (Windows)
echo ============================================================
echo.

if not exist "%COMMON_DIR%" mkdir "%COMMON_DIR%"
if not exist "%PLATFORM_DIR%" mkdir "%PLATFORM_DIR%"

where python >nul 2>nul
if %errorlevel% neq 0 (
  echo ❌ 未检测到 python
  pause & exit /b 1
)

echo ✓ 检测到 Python

REM ============ 步骤 1: 下载 ============
echo.
echo 📦 步骤 1: 下载所有依赖到 %PLATFORM_DIR% ...
python -m pip download --dest "%PLATFORM_DIR%" -r requirements.txt 2>nul
if %errorlevel% neq 0 (
  echo ❌ pip download 失败
  pause & exit /b 1
)
echo ✓ 下载完成

REM ============ 步骤 2: 分离纯 Python 包 ============
echo.
echo 📦 步骤 2: 把纯 Python 包移至 common/ ...
python -c "import os, shutil; from pathlib import Path; p=Path(os.environ['PLATFORM_DIR']); c=Path(os.environ['COMMON_DIR']); c.mkdir(exist_ok=True); m=k=0
for whl in p.glob('*.whl'):
    parts=whl.name.split('-')
    if len(parts)>=5 and parts[-2]=='none' and parts[-3] in ('py2.py3','py3','py2','py') and parts[-1].endswith('.whl'):
        shutil.move(str(whl), str(c/whl.name)); m+=1
    else: k+=1
print(f'  ✓ 移到 common/: {m} 个'); print(f'  ✓ 留在 platform/: {k} 个')"

echo.
echo ============================================================
echo   ✅ 完成！
echo ============================================================
echo.
echo 📁 vendor\
echo     ├── common\        (纯 Python 包，跨平台)
echo     └── windows-x64\   (平台相关包)
echo.
echo 下一步：双击 start.bat 启动（启动时会自动用本地 wheel）
echo.
pause
