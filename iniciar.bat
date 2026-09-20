@echo off
setlocal
cd /d "%~dp0"
title EyeSync

rem Entorno virtual: ya creado; si falta, se crea con Python 3.11 del sistema
if not exist ".venv\Scripts\python.exe" (
    echo [EyeSync] Creando el entorno virtual...
    call "C:\Users\chito\AppData\Local\Programs\Python\Python311\python.exe" -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
    echo [EyeSync] ERROR: no pude crear el entorno virtual.
    pause
    exit /b 1
)

if not exist ".venv\.deps_ok" (
    echo [EyeSync] Instalando dependencias ^(solo la primera vez, unos minutos^)...
    call ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
    call ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
    if errorlevel 1 (
        echo [EyeSync] ERROR instalando dependencias.
        pause
        exit /b 1
    )
    type nul > ".venv\.deps_ok"
)

".venv\Scripts\python.exe" main.py %*
echo.
pause
