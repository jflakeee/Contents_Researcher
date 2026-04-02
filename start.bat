@echo off
chcp 65001 >nul
title Contents Researcher - 시작

echo ============================================
echo  Contents Researcher 서버 시작
echo ============================================
echo.

set PROJECT_DIR=%~dp0

:: 백엔드 시작
echo [1/2] 백엔드 서버 시작 중 (포트 8000)...
cd /d "%PROJECT_DIR%backend"
start "CR-Backend" cmd /c "title CR-Backend && python -m uvicorn app.main:app --reload --port 8000 2>&1"

:: 프론트엔드 시작
echo [2/2] 프론트엔드 서버 시작 중 (포트 3000)...
cd /d "%PROJECT_DIR%frontend"
start "CR-Frontend" cmd /c "title CR-Frontend && pnpm dev 2>&1"

echo.
echo ============================================
echo  서버가 시작되었습니다!
echo.
echo  프론트엔드:  http://localhost:3000
echo  백엔드 API:  http://localhost:8000
echo  API 문서:    http://localhost:8000/docs
echo.
echo  종료하려면 stop.bat 을 실행하세요.
echo ============================================
echo.

:: 3초 후 브라우저 자동 열기
timeout /t 3 /nobreak >nul
start http://localhost:3000
