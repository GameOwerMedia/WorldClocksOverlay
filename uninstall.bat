@echo off
setlocal

reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "WorldClockOverlay" >nul 2>nul
if errorlevel 1 (
    echo Autostart was not installed.
) else (
    reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "WorldClockOverlay" /f >nul 2>nul
    if errorlevel 1 (
        echo Failed to remove autostart.
    ) else (
        echo Autostart removed.
    )
)

pause
