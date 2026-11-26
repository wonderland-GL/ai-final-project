@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 启动实验数据台...
python -m streamlit run app.py
pause
