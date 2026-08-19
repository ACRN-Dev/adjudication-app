@echo off
REM Batch helper to activate the project's virtual environment for cmd.exe
REM Usage: scripts\activate_venv.bat

SET "SCRIPT_DIR=%~dp0"
CD /D "%SCRIPT_DIR%.."
IF NOT EXIST ".venv\Scripts\activate.bat" (
  echo Virtual environment activation script not found at .venv\Scripts\activate.bat
  exit /b 1
)

call ".venv\Scripts\activate.bat"
echo Activated virtual environment from .venv\Scripts\activate.bat
