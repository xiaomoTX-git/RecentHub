@echo off
cd /d "%~dp0"
echo Cleaning up previous instances...
rem 只结束本目录 .venv 启动的 pythonw (即本项目的 RecentHub)，
rem 不能用 taskkill /F /IM pythonw.exe —— 那会误杀机器上所有 pythonw 进程
powershell -NoProfile -ExecutionPolicy Bypass -Command "$exe = '%~dp0.venv\Scripts\pythonw.exe'; Get-CimInstance Win32_Process -Filter Name='pythonw.exe' | Where-Object { $_.ExecutablePath -eq $exe } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 1 /nobreak >nul 2>&1
echo Starting RecentHub (Glass Edition)...
start "" ".venv\Scripts\pythonw.exe" "main.py" %*