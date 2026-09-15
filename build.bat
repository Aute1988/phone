@echo off
chcp 65001 >nul
REM ============================================================================
REM 📦 构建脚本 - Windows
REM 将手机号去重工具打包成单文件夹绿色版
REM
REM 使用方法：双击 build.bat
REM
REM 产物位置：dist\phone_dedup_tool\
REM 内部结构：
REM   phone_dedup_tool.exe       ← 主程序（双击启动）
REM   start.bat                  ← 中文启动脚本（双击这个就行）
REM   _internal\                 ← Python / pandas / numpy 等依赖
REM   使用说明.txt                ← 客户必读
REM ============================================================================

cd /d "%~dp0"

echo ============================================================
echo   📦 开始构建...
echo ============================================================

where python >nul 2>nul
if %errorlevel% neq 0 (
  echo ❌ 未检测到 python
  pause & exit /b 1
)

REM 安装 PyInstaller
python -m pip show pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
  echo 📦 安装 PyInstaller...
  python -m pip install --quiet --disable-pip-version-check pyinstaller
  if %errorlevel% neq 0 (
    echo ❌ PyInstaller 安装失败
    pause & exit /b 1
  )
  echo ✓ 安装完成
)

echo ✓ PyInstaller 版本:
python -m PyInstaller --version

REM 安装项目依赖（打包需要）
echo.
echo 📦 安装项目依赖...
python -m pip install --quiet --disable-pip-version-check -r requirements.txt

REM 清理旧构建（注意：不要删 *.spec）
echo.
echo 🧹 清理旧构建...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo ✓ 已清理

REM 构建
echo.
echo 🔨 开始打包（首次约 3-5 分钟）...
echo    （pandas / numpy 体积大，会慢一些）
python -m PyInstaller phone_dedup.spec --noconfirm --clean
if %errorlevel% neq 0 (
  echo.
  echo ❌ 构建失败，请检查上方错误信息
  pause & exit /b 1
)

REM 检查结果
if exist "dist\phone_dedup_tool\phone_dedup_tool.exe" (
  echo.
  echo ============================================================
  echo   ✅ 构建成功！
  echo ============================================================
  echo.
  echo 📁 产物位置: dist\phone_dedup_tool\
  echo 📊 文件夹大小:
  for /f "tokens=*" %%s in ('powershell -NoProfile -Command "(Get-ChildItem 'dist\phone_dedup_tool' -Recurse | Measure-Object Length -Sum).Sum / 1MB"') do echo    %%s MB
  echo.
  echo 🎉 分发给客户：把整个 dist\phone_dedup_tool\ 文件夹打包成 zip
  echo    客户解压后双击 start.bat 即可使用
  echo    （数据存在 %%APPDATA%%\手机号去重工具\）
  echo.
  echo 📝 下一步：手动把 start.bat 和 使用说明.txt 复制到 dist\phone_dedup_tool\
  echo.
  echo 按任意键打开 dist 文件夹...
  pause >nul
  explorer dist\phone_dedup_tool
) else (
  echo.
  echo ❌ 构建失败，dist\phone_dedup_tool\phone_dedup_tool.exe 未生成
  pause & exit /b 1
)
