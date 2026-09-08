@echo off
chcp 65001 > nul
title Kiwoom AI Quant Master Controller
color 0A

echo ========================================================
echo 🚀 Kiwoom REST API AI Auto-Trading System Booting...
echo ========================================================

:: 1. FastAPI 백엔드 및 AI 트레이딩 엔진 기동
echo [1/3] Starting Python FastAPI Backend (Port 8000)...
start "AI Backend Server" cmd /c "cd /d D:\04-py프로그램\kiwoom_ai\backend && call ..\.venv\Scripts\activate && python run_api_server.py"

:: 2. Next.js 웹 대시보드 기동
echo [2/3] Starting Next.js Web Dashboard (Port 3000)...
start "Next.js Web Console" cmd /c "cd /d D:\04-py프로그램\kiwoom_ai\frontend && npm run dev"

:: 3. 대기 시간 부여 (서버 안정화 대기)
timeout /t 5 /nobreak > nul

:: 4. Flutter 모바일 앱 웹 브라우저 테스트 모드 기동 (선택적)
echo [3/3] Starting Flutter Mobile App Monitor...
start "Flutter Mobile Monitor" cmd /c "cd /d D:\04-py프로그램\kiwoom_ai\mobile && flutter run -d chrome --web-port 5000"

echo ========================================================
echo ✅ All Microservices are running independently.
echo - Backend API: http://localhost:8000
echo - Web Dashboard: http://localhost:3000
echo - Mobile Monitor: http://localhost:5000
echo ========================================================
pause