@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo [Handoff] Python nao encontrado. Instale Python 3.12+ e reabra o terminal.
  if not defined WT_SESSION pause
  exit /b 1
)
python scripts\dev.py %*
if errorlevel 1 (
  echo.
  echo [Handoff] Falha no setup ou inicializacao. Consulte o erro acima.
  if not defined WT_SESSION pause
  exit /b 1
)
exit /b 0
