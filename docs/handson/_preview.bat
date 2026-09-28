@echo off
cd /d "%~dp0.."
echo Local preview server for docs/ (close this window to stop)
start "" http://127.0.0.1:8765/handson/
python -m http.server 8765 --bind 127.0.0.1
