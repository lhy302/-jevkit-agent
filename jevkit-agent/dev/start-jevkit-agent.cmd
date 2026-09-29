@echo off
rem ============================================================
rem  JevKit Agent - Windows launcher
rem  Double-click this file, or run it from a terminal.
rem ============================================================
setlocal enableextensions
cd /d "%~dp0"
set "RC=1"

if exist "%~dp0..\jevkit-agent.exe" (
    "%~dp0..\jevkit-agent.exe" %*
    set "RC=%ERRORLEVEL%"
    goto :finish
)

if exist "%~dp0jevkit-agent.exe" (
    "%~dp0jevkit-agent.exe" %*
    set "RC=%ERRORLEVEL%"
    goto :finish
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 "%~dp0jevkit-agent.py" %*
    set "RC=%ERRORLEVEL%"
    goto :finish
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python "%~dp0jevkit-agent.py" %*
    set "RC=%ERRORLEVEL%"
    goto :finish
)

echo.
echo [ERROR] Neither jevkit-agent.exe nor a Python 3 interpreter was found.
echo.
pause
exit /b 1

:finish
exit /b %RC%
