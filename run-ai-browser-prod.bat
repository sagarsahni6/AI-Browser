@echo off
title AI Browser 2.0 (Production)
cd /d "%~dp0"
echo ========================================================
echo Starting AI Browser 2.0 (Production Standalone)...
echo ========================================================
npx electron apps/desktop
pause
