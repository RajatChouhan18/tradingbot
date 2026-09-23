@echo off
title Stop Bot
echo Stopping Price Action Bot process...
taskkill /F /FI "WINDOWTITLE eq Price Action Trading Bot*" /T >nul 2>&1
echo Done! All associated bot windows have been closed.
pause
