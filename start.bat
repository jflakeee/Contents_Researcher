@echo off
chcp 65001 >nul 2>&1
title Contents Researcher

echo ============================================
echo  Contents Researcher 서버 시작
echo ============================================
echo.

set PROJECT_DIR=%~dp0

echo [1/2] 백엔드 서버 시작 중 (포트 8000)...
cd /d "%PROJECT_DIR%backend"
start "CR-Backend" cmd /k "chcp 65001 >nul 2>&1 && title CR-Backend && python -m uvicorn app.main:app --reload --port 8000"

echo [2/2] 프론트엔드 서버 시작 중 (포트 3000)...
cd /d "%PROJECT_DIR%frontend"
start "CR-Frontend" cmd /k "chcp 65001 >nul 2>&1 && title CR-Frontend && pnpm dev"

echo.
echo ============================================
echo  서버가 시작되었습니다!
echo.
echo  프론트엔드:  http://localhost:3000
echo  백엔드 API:  http://localhost:8000
echo  API 문서:    http://localhost:8000/docs
echo.
echo  종료: stop.bat 실행
echo ============================================

timeout /t 5 /nobreak >nul
start http://localhost:3000
