@echo off
cd /d "%~dp0"
set PYTHONPATH=.
.venv\Scripts\python.exe tests\take_glass_shots.py
