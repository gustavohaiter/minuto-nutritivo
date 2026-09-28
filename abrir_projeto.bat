@echo off
cd /d %~dp0

if not exist .venv (
    echo Ambiente virtual nao encontrado nessa pasta.
    echo Rode primeiro: python -m venv .venv ^&^& .venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo Ambiente virtual ativado. Pasta: %cd%
echo.
cmd /k
