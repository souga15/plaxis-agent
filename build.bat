@echo off
title PlaxisAI Build
echo ====================================================
echo   Building PlaxisAI.exe (single-file desktop app)
echo ====================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed! Install Python 3.11+ first.
    pause
    exit /b
)

:: Install build dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Building executable with PyInstaller...
python -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --name PlaxisAI ^
    --icon NONE ^
    --add-data "dashboard;dashboard" ^
    --add-data "tools;tools" ^
    --add-data "providers;providers" ^
    --add-data "templates;templates" ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.protocols ^
    --hidden-import uvicorn.protocols.http ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import uvicorn.protocols.websockets ^
    --hidden-import uvicorn.protocols.websockets.auto ^
    --hidden-import uvicorn.lifespan ^
    --hidden-import uvicorn.lifespan.on ^
    --hidden-import uvicorn.lifespan.off ^
    --hidden-import webview ^
    --collect-all webview ^
    app.py

echo.
if exist dist\PlaxisAI.exe (
    echo ====================================================
    echo   SUCCESS! PlaxisAI.exe created in dist\ folder
    echo ====================================================
    echo.
    echo File: dist\PlaxisAI.exe
    echo Size:
    for %%A in (dist\PlaxisAI.exe) do echo   %%~zA bytes
    echo.
    echo To distribute: just share PlaxisAI.exe
    echo Users double-click it and configure API keys in Settings tab.
) else (
    echo BUILD FAILED. Check errors above.
)
echo.
pause
