@echo off
set PYTHONUTF8=1
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 -X utf8 run.py --open
) else (
  python -X utf8 run.py --open
)
pause
