@echo off
chcp 65001 >nul
cd /d %~dp0

echo 正在启动 Celery Worker（Windows 使用 solo 进程池）...
.venv\Scripts\celery.exe -A app.core.celery_app.celery_app worker --pool=solo --loglevel=info

pause
