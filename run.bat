@echo off
cd /d "%~dp0"
rem NOTE: keep this file ASCII-only -- cmd.exe reads .bat with the OEM
rem codepage (GBK on zh-CN), so non-ASCII comments break line parsing.
echo Cleaning up previous instances...
rem Kill only the pythonw.exe launched from this folder's .venv (i.e. this
rem project's RecentHub). Do NOT use "taskkill /F /IM pythonw.exe" -- that
rem would kill every pythonw process on the machine.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$exe = '%~dp0.venv\Scripts\pythonw.exe'; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'pythonw.exe' -and $_.ExecutablePath -eq $exe } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 1 /nobreak >nul 2>&1
echo Starting RecentHub (Glass Edition)...
start "" ".venv\Scripts\pythonw.exe" "main.py" %*