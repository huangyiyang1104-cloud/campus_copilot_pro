@echo off
chcp 65001 >nul
title Campus Redis Tunnel

:loop
echo 正在建立 SSH 隧道...
ssh -N my-server
echo 隧道已断开，5 秒后自动重连...
timeout /t 5 >nul
goto loop
