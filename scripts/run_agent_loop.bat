@echo off
setlocal enabledelayedexpansion

REM Resolve workspace from this script location
set WORKSPACE=%~dp0..
cd /d "%WORKSPACE%"

set PYTHON=C:\Users\User\miniforge3\python.exe
set AGENT_LOG=.agent\agent_loop.log

if not exist .agent mkdir .agent

echo [%date% %time%] Starting agent loop >> "%AGENT_LOG%"

REM Never run automation from main branch
for /f "delims=" %%B in ('git branch --show-current') do set CURR_BRANCH=%%B
if /I "%CURR_BRANCH%"=="main" (
  echo [%date% %time%] ERROR: Refusing to run on main branch. Switch to dev first. >> "%AGENT_LOG%"
  exit /b 1
)

REM Delegate orchestration to PowerShell for better JSON/log handling
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_agent_loop.ps1 >> "%AGENT_LOG%" 2>&1
if %ERRORLEVEL% neq 0 (
  echo [%date% %time%] ERROR: run_agent_loop.ps1 failed with exit %ERRORLEVEL% >> "%AGENT_LOG%"
  exit /b %ERRORLEVEL%
)

echo [%date% %time%] Agent loop complete >> "%AGENT_LOG%"
exit /b 0
