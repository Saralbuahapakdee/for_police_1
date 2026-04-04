@echo off
REM ============================================================
REM  release.bat - Build, tag, and push Docker images
REM  Usage:  release.bat 1.0.0
REM ============================================================

set DOCKER_USER=tatanoi007
set BACKEND=weapon-detection-backend
set FRONTEND=weapon-detection-frontend

set VERSION=%1
if "%VERSION%"=="" (
    echo Error: Please provide a version number
    echo Usage: release.bat 1.0.0
    exit /b 1
)

echo.
echo ======================================
echo  Releasing v%VERSION%
echo ======================================
echo.

echo [1/4] Building backend...
docker build -t %DOCKER_USER%/%BACKEND%:%VERSION% -t %DOCKER_USER%/%BACKEND%:latest ./backend
if %ERRORLEVEL% neq 0 ( echo Build failed! & exit /b 1 )

echo.
echo [2/4] Building frontend...
docker build -t %DOCKER_USER%/%FRONTEND%:%VERSION% -t %DOCKER_USER%/%FRONTEND%:latest ./frontend
if %ERRORLEVEL% neq 0 ( echo Build failed! & exit /b 1 )

echo.
echo [3/4] Pushing backend...
docker push %DOCKER_USER%/%BACKEND%:%VERSION%
docker push %DOCKER_USER%/%BACKEND%:latest

echo.
echo [4/4] Pushing frontend...
docker push %DOCKER_USER%/%FRONTEND%:%VERSION%
docker push %DOCKER_USER%/%FRONTEND%:latest

echo.
echo ======================================
echo  v%VERSION% released successfully!
echo ======================================
echo.
echo  Pushed:
echo    %DOCKER_USER%/%BACKEND%:%VERSION%
echo    %DOCKER_USER%/%BACKEND%:latest
echo    %DOCKER_USER%/%FRONTEND%:%VERSION%
echo    %DOCKER_USER%/%FRONTEND%:latest
echo.
