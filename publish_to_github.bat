@echo off
title Publishing PupuSnipe to GitHub...
cd /d "%~dp0"
echo ======================================================================
echo  Publishing PupuSnipe to https://github.com/SyphoxYt/pupu-snipes
echo ======================================================================

set "GIT_EXE=C:\Program Files\Git\cmd\git.exe"
if not exist "%GIT_EXE%" (
    where git >nul 2>nul
    if %errorlevel% equ 0 (
        set "GIT_EXE=git"
    ) else (
        echo [!] Git not found.
        pause
        exit /b 1
    )
)

echo [*] Using Git at: %GIT_EXE%

"%GIT_EXE%" init
"%GIT_EXE%" branch -M main
"%GIT_EXE%" remote remove origin >nul 2>nul
"%GIT_EXE%" remote add origin https://github.com/SyphoxYt/pupu-snipes.git
"%GIT_EXE%" config user.name "SyphoxYt"
"%GIT_EXE%" config user.email "syphox@users.noreply.github.com"

echo [*] Staging files...
"%GIT_EXE%" add .

echo [*] Committing...
"%GIT_EXE%" commit -m "feat: PupuSnipe Sol's RNG sniper with 10-minute cooldown, context log, and engine optimizations"

echo [*] Pushing to https://github.com/SyphoxYt/pupu-snipes...
"%GIT_EXE%" push -u origin main
if %errorlevel% neq 0 (
    echo.
    echo [*] Pulling with rebase in case repository has initial commit on GitHub...
    "%GIT_EXE%" pull origin main --rebase --allow-unrelated-histories
    echo [*] Pushing to main branch...
    "%GIT_EXE%" push -u origin main
)

echo.
echo ======================================================================
echo  Done! View repository at https://github.com/SyphoxYt/pupu-snipes
echo ======================================================================
pause
