@echo off
setlocal

reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "WorldClockOverlay" /f

echo Autostart removed.
pause
