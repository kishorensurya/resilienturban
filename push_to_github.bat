@echo off
title Push ResilientUrban to GitHub
cd /d "C:\Users\KISHORE\.gemini\antigravity-ide\scratch\resilient_urban"
echo ============================================================
echo   Pushing ResilientUrban to:
echo   https://github.com/kishorensurya/resilienturban
echo ============================================================
echo.
git push -u origin main
echo.
if %errorlevel% equ 0 (
    echo ============================================================
    echo   SUCCESS! Repository pushed to GitHub!
    echo   Open: https://github.com/kishorensurya/resilienturban
    echo ============================================================
) else (
    echo.
    echo Push could not complete. Check authentication above.
)
pause
