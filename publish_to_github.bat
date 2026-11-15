@echo off
title Publishing PupuSnipe to GitHub & Releases...
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

"%GIT_EXE%" config user.name "SyphoxYt"
"%GIT_EXE%" config user.email "syphox@users.noreply.github.com"

echo [*] Staging files...
"%GIT_EXE%" add .

echo [*] Committing...
"%GIT_EXE%" commit -m "feat: xe33hunt protocol sync & web gateway client routing (v1.1.5)"

echo [*] Setting tags 1.1.5 and v1.1.5...
"%GIT_EXE%" tag -f 1.1.5
"%GIT_EXE%" tag -f v1.1.5

echo [*] Pushing to https://github.com/SyphoxYt/pupu-snipes (main + tags)...
"%GIT_EXE%" push -u origin main 1.1.5 v1.1.5 --force
if %errorlevel% neq 0 (
    echo.
    echo [*] Retrying push with rebase pull...
    "%GIT_EXE%" pull origin main --rebase --allow-unrelated-histories
    echo [*] Pushing to main branch...
    "%GIT_EXE%" push -u origin main 1.1.5 v1.1.5 --force
)

echo.
echo [*] Publishing release asset (PupuSnipe-v1.1.5-win64.zip) to GitHub Releases...
python publish_release.py

echo.
echo ======================================================================
echo  Done! View repository at https://github.com/SyphoxYt/pupu-snipes
echo ======================================================================
pause
