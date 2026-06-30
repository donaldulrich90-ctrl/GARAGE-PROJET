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
    echo  [1/3] Creation de l'environnement virtuel...
    python -m venv venv
    echo  [2/3] Installation des dependances ^(patientez^)...
    venv\Scripts\pip install -r requirements.txt --quiet
)

:: Initialiser la base de donnees si absente
if not exist "db.sqlite3" (
    echo  [3/3] Initialisation de la base de donnees...
    venv\Scripts\python manage.py migrate
    venv\Scripts\python manage.py shell < seed_demo.py
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
