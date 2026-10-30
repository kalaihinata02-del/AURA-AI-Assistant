@echo off
REM ─────────────────────────────────────────────────────────────
REM  AURA GitHub Publisher — Run this after Git is installed
REM  Double-click this file OR run from Command Prompt
REM ─────────────────────────────────────────────────────────────

set GITHUB_USER=kalaihinata02-del
set REPO_NAME=AURA-AI-Assistant
set PROJECT=d:\Kalai\Assistant

echo.
echo ============================================================
echo   Publishing AURA to GitHub as @%GITHUB_USER%
echo ============================================================
echo.

cd /d "%PROJECT%"

echo [1/6] Initializing Git repo...
git init -b main

echo.
echo [2/6] Setting Git identity...
git config user.name "%GITHUB_USER%"
git config user.email "%GITHUB_USER%@users.noreply.github.com"

echo.
echo [3/6] Staging all files (secrets excluded by .gitignore)...
git add .

echo.
echo [4/6] First commit...
git commit -m "Initial commit: AURA AI Assistant v1.0 - Multilingual Voice AI"

echo.
echo [5/6] Adding remote...
git remote add origin https://github.com/%GITHUB_USER%/%REPO_NAME%.git

echo.
echo [6/6] Pushing to GitHub...
echo *** A browser/login prompt may appear — sign in to GitHub ***
git push -u origin main

echo.
echo ============================================================
if %errorlevel%==0 (
    echo   SUCCESS! AURA is live at:
    echo   https://github.com/%GITHUB_USER%/%REPO_NAME%
) else (
    echo   Push failed. Check the error above.
    echo   Make sure the repo exists at:
    echo   https://github.com/%GITHUB_USER%/%REPO_NAME%
    echo   and it is EMPTY (no README added)
)
echo ============================================================
pause
