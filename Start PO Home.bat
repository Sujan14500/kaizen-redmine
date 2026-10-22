@echo off
REM Starts PO Home without a black window. Keep this file next to po_home.py
cd /d "%~dp0"
where pythonw >NUL 2>NUL
if %errorlevel%==0 (
    start "" pythonw po_home.py
    exit /b
)
where pyw >NUL 2>NUL
if %errorlevel%==0 (
    start "" pyw po_home.py
    exit /b
)
python po_home.py
if errorlevel 1 pause
