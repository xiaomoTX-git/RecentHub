@echo off
setlocal
cd /d "%~dp0"

rem ============================================================
rem  RecentHub Portable Build
rem  Reuses the same PyInstaller output as the installer, adds a
rem  portable.flag marker and packs everything into a zip.
rem  NOTE: keep this file ASCII-only -- cmd.exe reads .bat with the
rem  OEM codepage (GBK on zh-CN), so non-ASCII text breaks parsing.
rem ============================================================

rem Derive APP_VERSION from app\core\version.py (single source of truth,
rem so the zip name can never drift from the app's self-reported version)
for /f %%A in ('powershell -NoProfile -Command "(Select-String -Path 'app\core\version.py' -Pattern 'APP_VERSION').Line.Split([char]34)[1]"') do set VERSION=%%A
if not defined VERSION (
    echo FAILED to read APP_VERSION from app\core\version.py
    exit /b 1
)

echo ============================================
echo   RecentHub Portable Build  v%VERSION%
echo ============================================

echo [1/4] Cleaning previous output...
if exist "dist\RecentHub" rmdir /s /q "dist\RecentHub"
if exist "build\RecentHub" rmdir /s /q "build\RecentHub"

echo [2/4] Running PyInstaller...
".venv\Scripts\pyinstaller.exe" --noconfirm --clean RecentHub.spec
if errorlevel 1 goto :fail

echo [3/4] Writing portable.flag marker...
rem This file sits next to RecentHub.exe; on startup the app detects it
rem and redirects config / database / logs into exe\data (portable mode)
> "dist\RecentHub\portable.flag" echo portable

echo [4/4] Compressing to RecentHub_portable_v%VERSION%.zip...
if exist "dist\RecentHub_portable_v%VERSION%.zip" del /q "dist\RecentHub_portable_v%VERSION%.zip"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\RecentHub\*' -DestinationPath 'dist\RecentHub_portable_v%VERSION%.zip' -Force"
if errorlevel 1 goto :fail

echo.
echo Build finished: dist\RecentHub_portable_v%VERSION%.zip
goto :eof

:fail
echo.
echo Build FAILED, please check the log above.
exit /b 1