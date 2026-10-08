@echo off
title RESILIENTURBAN - Hyper-Local Flood Early Warning System
color 0B
echo =====================================================================
echo  RESILIENTURBAN - Hyper-Local Flood Warning & Action Network
echo  Hazard Focus: URBAN FLOODING ONLY
echo  Customer Support Helpline: 8431535534 | civora@gmail.com
echo =====================================================================
echo.
echo [1/3] Checking dependencies...
py -m pip install -r requirements.txt
echo.
echo [2/3] Initializing SQLite database & ML Model...
py database.py
echo.
echo [3/3] Starting Flask Application on http://127.0.0.1:5000 ...
echo Press Ctrl+C to terminate the server.
echo.
py app.py
pause
