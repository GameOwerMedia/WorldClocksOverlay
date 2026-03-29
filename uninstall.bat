@echo off
setlocal

echo Cleaning up WorldClockOverlay...

reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "WorldClockOverlay" >nul 2>nul
if not errorlevel 1 (
    reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "WorldClockOverlay" /f >nul 2>nul
    if errorlevel 1 (
        echo Failed to remove autostart entry.
    ) else (
        echo Autostart entry removed.
    )
) else (
    echo No autostart entry found.
)

if exist dist (
    rmdir /S /Q dist >nul 2>nul
    echo Build output removed.
)

if exist build (
    rmdir /S /Q build >nul 2>nul
)

if exist *.spec (
    del /F /Q *.spec >nul 2>nul
)

echo.
echo Cleanup complete.
pause
