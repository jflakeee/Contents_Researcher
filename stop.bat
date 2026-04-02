@echo off
chcp 65001 >nul
title Contents Researcher - 종료

echo ============================================
echo  Contents Researcher 서버 종료
echo ============================================
echo.

:: uvicorn (백엔드) 프로세스 종료
echo [1/2] 백엔드 서버 종료 중...
taskkill /fi "WINDOWTITLE eq CR-Backend*" /f >nul 2>&1
taskkill /im uvicorn.exe /f >nul 2>&1

:: node (프론트엔드) 프로세스 종료
echo [2/2] 프론트엔드 서버 종료 중...
taskkill /fi "WINDOWTITLE eq CR-Frontend*" /f >nul 2>&1

:: 포트 점유 프로세스 강제 종료
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /pid %%a /f >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do taskkill /pid %%a /f >nul 2>&1

echo.
echo  모든 서버가 종료되었습니다.
echo ============================================
