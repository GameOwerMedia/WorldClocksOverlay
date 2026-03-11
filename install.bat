@echo off
setlocal

set "EXE_PATH=dist\WorldClockOverlay.exe"

echo [1/5] Preparing virtual environment...
if not exist .venv (
    py -m venv .venv
    if errorlevel 1 goto :fail
)

call .venv\Scripts\activate.bat
if errorlevel 1 goto :fail

echo [2/5] Installing dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto :fail

pip install -r requirements.txt
if errorlevel 1 goto :fail

pip install pyinstaller
if errorlevel 1 goto :fail

echo [3/5] Building EXE...
if exist "%EXE_PATH%" (
    del /F /Q "%EXE_PATH%" >nul 2>nul
    if exist "%EXE_PATH%" (
        echo.
        echo Build failed: "%EXE_PATH%" is locked.
        echo Close the running app and try again.
        goto :fail
    )
)

python -m PyInstaller --noconfirm --onefile --windowed --name WorldClockOverlay --add-data "config.json;." app.py
if errorlevel 1 goto :fail

if not exist dist mkdir dist
copy /Y config.json dist\config.json >nul
if errorlevel 1 goto :fail

if not exist "%EXE_PATH%" (
    echo.
    echo Build failed: EXE was not created.
    goto :fail
)

echo [4/5] Asking about autostart...
set /p AUTOSTART=Install autostart for current Windows user? (Y/N): 

if /I "%AUTOSTART%"=="Y" (
    reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "WorldClockOverlay" /t REG_SZ /d "\"%cd%\%EXE_PATH%\"" /f
    if errorlevel 1 goto :fail
    echo Autostart installed.
) else (
    echo Autostart skipped.
)

echo [5/5] Done.
echo.
echo Launch the app using:
echo %EXE_PATH%
pause
exit /b 0

:fail
echo.
echo Install/build did not complete successfully.
pause
exit /b 1
