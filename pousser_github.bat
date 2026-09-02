@echo off
chcp 65001 >nul
title Push GitHub - garage_saas
cd /d D:\garage_saas

echo ==================================================
echo    PUSH GITHUB  -  garage_saas  (branche main)
echo ==================================================
echo.

REM 1) Supprimer un eventuel verrou Git bloque
if exist ".git\index.lock" del /f /q ".git\index.lock"

REM 2) Afficher les fichiers modifies
echo --- Fichiers modifies : ---
git status -s
echo.

REM 3) Avertissement production
echo ATTENTION : pousser sur "main" redeploie l'application en PRODUCTION
echo (Coolify -^> gegarage.duckdns.org).
echo.
set /p CONF=Continuer le push ? (o/n) : 
if /i not "%CONF%"=="o" goto :annule

REM 4) Message de commit (Entree = message auto avec la date)
set "MSG="
set /p MSG=Message du commit (Entree = message auto) : 
if "%MSG%"=="" set "MSG=mise a jour %date% %time%"

REM 5) Ajouter, commiter, pousser
echo.
git add -A
git commit -m "%MSG%"
git push
if errorlevel 1 (
  echo.
  echo [i] Premier push : configuration de la branche distante...
  git push -u origin main
)

echo.
echo ==================================================
echo    TERMINE
echo ==================================================
goto :fin

:annule
echo.
echo Push annule. Aucune modification envoyee.

:fin
echo.
pause
