@echo off
title PupuSnipe Launcher
cd /d "%~dp0"
if exist "PupuSnipe.exe" (
    start "" "PupuSnipe.exe"
) else if exist "dist\PupuSnipe\PupuSnipe.exe" (
    start "" "dist\PupuSnipe\PupuSnipe.exe"
) else (
    echo Python environment starting...
    python main.py
)
exit
