@echo off
title Price Action Trading Bot (TradingView Feed)
color 0A

:: Change directory to current folder
cd /d "%~dp0"

echo ================================================================
echo           PRICE ACTION TRADING BOT RUNNER (AUTO-RESTART)
echo ================================================================
echo Current Directory: %CD%
echo Starting bot at: %date% %time%
echo Press Ctrl + C to stop the bot.
echo ================================================================
echo.

:loop
echo [%time%] Launching bot...
python pdf_price_action_bot_v3_tradingview.py

echo.
echo ================================================================
echo [WARNING] Bot process stopped or disconnected at: %date% %time%
echo Restarting automatically in 5 seconds... (Press Ctrl+C to abort)
echo ================================================================
timeout /t 5 /nobreak >nul
goto loop
