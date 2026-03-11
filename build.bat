@echo off
setlocal

if not exist .venv (
    py -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --noconfirm --onefile --windowed --name WorldClockOverlay --add-data "config.json;." app.py

if not exist dist mkdir dist
copy /Y config.json dist\config.json >nul

echo.
echo Build completed.
echo EXE: dist\WorldClockOverlay.exe
pause
