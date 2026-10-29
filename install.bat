@echo off
setlocal
cd /d "%~dp0"

set "EXE_PATH=dist\WorldClockOverlay.exe"

echo [1/3] Preparing virtual environment...
if not exist .venv (
    py -m venv .venv
    if errorlevel 1 goto :fail
)

call .venv\Scripts\activate.bat
if errorlevel 1 goto :fail

echo [2/3] Installing dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto :fail

pip install -r requirements.txt
if errorlevel 1 goto :fail

pip install "pyinstaller>=6.3"
if errorlevel 1 goto :fail

echo [3/3] Building EXE...
if exist "%EXE_PATH%" (
    del /F /Q "%EXE_PATH%" >nul 2>nul
    if exist "%EXE_PATH%" (
        echo.
        echo Build failed: "%EXE_PATH%" is locked.
        echo Close the running app and try again.
        goto :fail
    )
)

python -m PyInstaller --noconfirm --onefile --windowed --name WorldClockOverlay --add-data "config.json;." --collect-all tzdata app.py
if errorlevel 1 goto :fail

if not exist dist mkdir dist
if not exist "dist\config.json" (
    copy /Y "config.json" "dist\config.json" >nul
    if errorlevel 1 goto :fail
)

if not exist "%EXE_PATH%" (
    echo.
    echo Build failed: EXE was not created.
    goto :fail
)

echo.
echo Build completed.
echo EXE: %EXE_PATH%
pause
exit /b 0

:fail
echo.
echo Install/build did not complete successfully.
pause
exit /b 1
