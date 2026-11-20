@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo [1/4] Preparing virtualenv...
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"

echo [2/4] Installing app and PyInstaller...
python -m pip install -U pip
python -m pip install -e .
python -m pip install pyinstaller

echo [3/4] Building windowed exe (tkinter, no console)...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller --noconfirm --clean --windowed --onedir ^
  --name ScheduleAssistant ^
  --paths src ^
  --collect-all chinese_calendar ^
  --collect-all tzdata ^
  --collect-all pystray ^
  --hidden-import jwt ^
  --hidden-import cryptography ^
  --hidden-import PIL._tkinter_finder ^
  --hidden-import schedule_assistant ^
  --add-data "src\schedule_assistant\assets\fonts;schedule_assistant/assets/fonts" ^
  --add-data "src\schedule_assistant\assets\images;schedule_assistant/assets/images" ^
  src\schedule_assistant\main.py

if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

echo [4/4] Done.
echo Double-click: "%~dp0dist\ScheduleAssistant\ScheduleAssistant.exe"
explorer "%~dp0dist\ScheduleAssistant"
endlocal
