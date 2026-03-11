@echo off
setlocal

echo [1/5] Preparing virtual environment...
if not exist .venv (
    py -m venv .venv
)

call .venv\Scripts\activate.bat

echo [2/5] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo [3/5] Building EXE...
pyinstaller --noconfirm --onefile --windowed --name WorldClockOverlay --add-data "config.json;." app.py

if not exist dist mkdir dist
copy /Y config.json dist\config.json >nul

echo [4/5] Asking about autostart...
set /p AUTOSTART=Install autostart for current Windows user? (Y/N): 

if /I "%AUTOSTART%"=="Y" (
    reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "WorldClockOverlay" /t REG_SZ /d "\"%cd%\dist\WorldClockOverlay.exe\"" /f
    echo Autostart installed.
) else (
    echo Autostart skipped.
)

echo [5/5] Done.
echo.
echo Launch the app using:
echo dist\WorldClockOverlay.exe
pause
