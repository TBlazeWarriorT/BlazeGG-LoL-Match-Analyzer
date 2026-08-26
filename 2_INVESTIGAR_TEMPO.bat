@echo off
chcp 65001 > nul
cls
python investigar_tempo.py
echo.
echo Esta janela será fechada automaticamente em 10 segundos...
timeout /t 10 > nul
