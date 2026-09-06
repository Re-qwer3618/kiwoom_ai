@echo off
:: 한글 깨짐 방지 (UTF-8)
chcp 65001 >nul
title Kiwoom AI Quant System Launcher

echo ===================================================
echo  [시스템 기동] 키움 REST API 기반 AI 자동매매 파이프라인
echo ===================================================

:: 1. 가상환경 및 워크스페이스 경로 설정
set VENV_PATH=D:\00-python\.venv\Scripts\activate
set WORKSPACE_PATH=D:\04-py프로그램\kiwoom_ai

:: 2. 터미널 1: 데이터 무결성 검증기 실행
echo [Terminal 1] 데이터 스토리지 무결성 검증 프로세스를 시작합니다.
start "Data Validator (Terminal 1)" cmd /k "call %VENV_PATH% && cd /d %WORKSPACE_PATH% && python run_validator.py"

:: 3. 터미널 2: FastAPI 게이트웨이 서버 실행
echo [Terminal 2] FastAPI 게이트웨이 및 웹소켓 서버를 시작합니다.
start "FastAPI Gateway (Terminal 2)" cmd /k "call %VENV_PATH% && cd /d %WORKSPACE_PATH% && python run_api_server.py"

echo.
echo [성공] 모든 프로세스가 분리된 터미널에서 실행되었습니다.
echo chart_monitor.html 파일을 열어 시각적 검증을 진행하십시오.
pause