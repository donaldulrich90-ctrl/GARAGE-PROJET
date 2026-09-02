@echo off
chcp 65001 >nul
title Garage SaaS
cd /d "%~dp0"

echo.
echo  ================================================
echo   GARAGE SAAS - Lancement en cours...
echo  ================================================
echo.

:: Creer l'environnement virtuel si absent
if not exist "venv\Scripts\python.exe" (
    echo  [1/4] Creation de l'environnement virtuel...
    python -m venv venv
)

echo  [2/4] Verification des dependances ^(patientez^)...
venv\Scripts\python -m pip install -r requirements.txt --quiet
if errorlevel 1 goto :error

:: Le lanceur Windows utilise le mode local et SQLite par defaut.
set "DJANGO_DEBUG=True"

set "GARAGE_DB_NOUVELLE=0"
if not exist "db.sqlite3" set "GARAGE_DB_NOUVELLE=1"

echo  [3/4] Mise a jour de la base de donnees...
venv\Scripts\python manage.py migrate --noinput
if errorlevel 1 goto :error

if "%GARAGE_DB_NOUVELLE%"=="1" (
    echo  [4/4] Creation des donnees de demonstration...
    venv\Scripts\python manage.py shell < seed_demo.py
    if errorlevel 1 goto :error
) else (
    echo  [4/4] Base existante conservee.
)

echo.
echo  ================================================
echo   Garage SaaS est pret !
echo   Adresse : http://127.0.0.1:8000
echo.
echo   Comptes de test :
echo   - admin_wayalghin / garage1234
echo   - platform_admin  / platform1234
echo.
echo   Fermez cette fenetre pour arreter le serveur.
echo  ================================================
echo.

:: Ouvrir le navigateur apres 2 secondes
start /b cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000"

:: Lancer le serveur
venv\Scripts\python manage.py runserver

echo.
pause
exit /b 0

:error
echo.
echo  Une erreur a interrompu le lancement. Consultez le message ci-dessus.
pause
exit /b 1
