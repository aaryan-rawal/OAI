@echo off
set "PROJECT_ROOT=%~dp0"
start "OptiFreight AI Backend" /D "%PROJECT_ROOT%" cmd /k "call run.bat"
timeout /t 3 /nobreak >nul
start "OptiFreight AI Frontend" /D "%PROJECT_ROOT%frontend" cmd /k "call run_frontend.bat"
