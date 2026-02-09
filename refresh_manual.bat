@echo off
cd /d %~dp0
python scripts\refresh_data.py --mode manual --user other_member
pause
