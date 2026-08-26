@echo off
chcp 65001 > nul
cls
echo ==================================================
echo   ABRINDO RELATÓRIO DA ÚLTIMA PARTIDA
echo ==================================================
echo.
python ver_ultima_partida.py
echo.
echo Esta janela será fechada automaticamente em 5 segundos...
timeout /t 5 > nul
