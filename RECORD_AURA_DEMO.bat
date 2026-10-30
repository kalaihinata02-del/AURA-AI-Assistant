@echo off
title AURA - Auto Demo Video Recorder
cd /d "D:\Kalai\Assistant"
echo ========================================================
echo    AURA - Automated Cinematic Demo Video Recorder
echo ========================================================
echo.
echo Make sure Aura window is open on your screen!
echo Demo will start in 5 seconds after launch.
echo.
.venv\Scripts\python.exe demo_recorder.py
pause
