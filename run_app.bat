@echo off
title Indian Railway Delay Cascade Analytics
echo Starting Streamlit Web Dashboard on http://localhost:8501 ...
set PYTHONPATH=.
.\.venv\Scripts\streamlit.exe run app\dashboard.py
pause
