@echo off
setlocal

if not exist .venv (
    py -m venv .venv
    if errorlevel 1 goto :fail
)

call .venv\Scripts\activate.bat
if errorlevel 1 goto :fail

python -m pip install --upgrade pip
if errorlevel 1 goto :fail

pip install -r requirements.txt
if errorlevel 1 goto :fail

python app.py
exit /b %errorlevel%

:fail
echo.
echo Development run could not start.
pause
exit /b 1
