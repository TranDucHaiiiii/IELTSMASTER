@echo off
title IELTS Master Hub - Server
echo ========================================================
echo       KHOI DONG HE THONG LUYEN THI IELTS MASTER HUB
echo ========================================================
echo.
cd /d "%~dp0"
if exist "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" app.py
) else (
    python app.py
)
pause
