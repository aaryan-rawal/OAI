@echo off
setlocal
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%frontend"
where node >nul 2>&1 || (echo [ERROR] Node.js 20+ is required.& exit /b 1)
node -e "process.exit(Number(process.versions.node.split('.')[0]) >= 20 ? 0 : 1)" || (echo [ERROR] Node.js 20 or newer is required.& exit /b 1)
where npm >nul 2>&1 || (echo [ERROR] npm is required.& exit /b 1)
if not exist "node_modules" (
  echo [INFO] Installing frontend dependencies from package-lock.json...
  call npm ci
  if errorlevel 1 exit /b 1
)
echo [INFO] Starting OptiFreight AI frontend at http://localhost:5173
call npm run dev
