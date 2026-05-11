@echo off
setlocal
cd /d "%~dp0\.."
python tools\webp_converter_gui.py
if errorlevel 1 pause
