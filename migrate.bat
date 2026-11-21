@echo off
setlocal
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"
if not exist ".venv\Scripts\python.exe" (echo [ERROR] Run setup.bat first.& exit /b 1)
set "PYTHONPATH=%PROJECT_ROOT%backend"
cd /d "%PROJECT_ROOT%backend"
echo [WARNING] This applies pending Alembic migrations to the configured PostgreSQL database.
echo [WARNING] Confirm you have a database backup before continuing.
set /p CONFIRM=Type APPLY to continue: 
if /I not "%CONFIRM%"=="APPLY" (echo Cancelled.& exit /b 0)
"%PROJECT_ROOT%.venv\Scripts\python.exe" -m alembic upgrade head
