@echo off
setlocal
cd /d "%~dp0"

rem ============================================================
rem  RecentHub 便携绿色版构建脚本
rem  与安装版共用同一份 PyInstaller 产物，仅多写一个 portable.flag
rem  标记文件并压缩为 zip 分发；解压即用，删除目录即卸载。
rem ============================================================

set VERSION=1.1.0

echo ============================================
echo   RecentHub Portable Build  v%VERSION%
echo ============================================

echo [1/4] 清理旧产物...
if exist "dist\RecentHub" rmdir /s /q "dist\RecentHub"
if exist "build\RecentHub" rmdir /s /q "build\RecentHub"

echo [2/4] PyInstaller 打包...
".venv\Scripts\pyinstaller.exe" --noconfirm --clean RecentHub.spec
if errorlevel 1 goto :fail

echo [3/4] 写入便携标记 portable.flag...
rem 该文件与 RecentHub.exe 同级，程序启动时据此判定便携模式，
rem 数据 / 数据库 / 日志改落 exe\data，实现随插随用
> "dist\RecentHub\portable.flag" echo portable

echo [4/4] 压缩为 RecentHub_portable_v%VERSION%.zip...
if exist "dist\RecentHub_portable_v%VERSION%.zip" del /q "dist\RecentHub_portable_v%VERSION%.zip"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\RecentHub\*' -DestinationPath 'dist\RecentHub_portable_v%VERSION%.zip' -Force"
if errorlevel 1 goto :fail

echo.
echo 构建完成: dist\RecentHub_portable_v%VERSION%.zip
goto :eof

:fail
echo.
echo 构建失败，请检查上方日志。
exit /b 1