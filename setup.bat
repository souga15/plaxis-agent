@echo off
title Plaxis AI Agent Installer
echo ====================================================
echo   Welcome to the Plaxis AI Agent Installer!
echo ====================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed on this laptop!
    echo Automatically installing Python for you via winget...
    echo Please accept any Windows administrator prompts that appear.
    echo.
    winget install --id Python.Python.3.11 --exact --silent --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo.
        echo Direct automatic installation failed.
        echo Please download and install Python 3.11 manually from:
        echo https://www.python.org/downloads/
        echo Make sure to check the box "Add Python to PATH" during installation.
        echo.
        pause
        exit /b
    )
    echo Python installed successfully! Please restart this setup.bat file to complete setup.
    pause
    exit /b
)

echo Python is installed.
echo Installing required Python packages...
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo ====================================================
echo   SUCCESS! All dependencies installed successfully.
echo ====================================================
echo.
echo Now, follow these simple steps to run:
echo 1. Open Plaxis 3D
echo 2. Go to Expert -> Configure remote scripting server
echo 3. Enable the server on port 10000 (no password)
echo 4. Double-click 'run.bat' in this folder!
echo.
pause
