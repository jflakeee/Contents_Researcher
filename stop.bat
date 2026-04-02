@echo off
chcp 65001 >nul 2>&1
title Contents Researcher - Stop

echo ============================================
echo  Contents Researcher 서버 종료
echo ============================================
echo.

echo [1/2] 백엔드 서버 종료 중...
taskkill /fi "WINDOWTITLE eq CR-Backend*" /f >nul 2>&1
taskkill /im uvicorn.exe /f >nul 2>&1

echo [2/2] 프론트엔드 서버 종료 중...
taskkill /fi "WINDOWTITLE eq CR-Frontend*" /f >nul 2>&1

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /pid %%a /f >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do taskkill /pid %%a /f >nul 2>&1

echo.
echo  모든 서버가 종료되었습니다.
echo ============================================
