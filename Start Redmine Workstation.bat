@echo off
REM Starts Redmine PO Workstation. Keep this file in the same folder as redmine_workstation.py
cd /d "%~dp0"
where pythonw >NUL 2>NUL
if %errorlevel%==0 (
    start "" pythonw redmine_workstation.py
) else (
    python redmine_workstation.py
    pause
)
