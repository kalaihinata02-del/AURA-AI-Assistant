@echo off
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0main.py" %*
) else (
    start "" wscript.exe "%~dp0start_aura.vbs"
)
exit /b 0
