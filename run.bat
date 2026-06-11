@echo off
chcp 65001 >nul
title 轻简日程管理

echo ================================
echo   轻简日程管理 - 启动中...
echo ================================
echo.

:: 检查 Python 是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python（python.org）
    echo 安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

:: 创建虚拟环境（首次运行）
if not exist "venv" (
    echo [首次运行] 正在创建虚拟环境...
    python -m venv venv
)

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 安装依赖（首次或有更新时）
echo [检查] 正在检查依赖...
pip install -r requirements.txt -q

:: 启动应用
echo [启动] 正在打开日程管理...
echo.
python main.py

:: 如果 python 异常退出，保持窗口查看错误
if %errorlevel% neq 0 (
    echo.
    echo [错误] 程序异常退出，请检查上方错误信息。
    pause
)
