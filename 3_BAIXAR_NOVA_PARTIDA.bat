@echo off
chcp 65001 > nul
cls
python baixar_partida.py
echo.
echo Esta janela será fechada automaticamente em 10 segundos...
timeout /t 10 > nul
