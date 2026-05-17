@echo off
REM Build vid2scan Windows executable
REM Run from project root with Python venv active

call venv\Scripts\activate.bat
pyinstaller vid2scan.spec --clean

echo Output: dist\vid2scan.exe
pause
