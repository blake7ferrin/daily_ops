@echo off
cd /d "%~dp0"
doppler run -- python -m src.main
exit /b %ERRORLEVEL%
