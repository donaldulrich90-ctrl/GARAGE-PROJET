@echo off
setlocal ENABLEEXTENSIONS
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  Push des changements vers GitHub
echo ========================================
echo.

if not exist .git goto not_repo

echo [1/6] Nettoyage du verrou git eventuel...
if exist .git\index.lock del /f /q .git\index.lock
echo.

echo [2/6] Restauration de settings.py...
git checkout HEAD -- garage_saas\settings.py
if errorlevel 1 goto err
echo.

echo [3/6] Reapplication des changements semantiques...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0patch_settings.ps1"
if errorlevel 1 goto err
echo.

echo [4/6] Fichiers modifies :
git status --short
echo.
git diff --stat garage_saas\settings.py
echo.

echo ========================================
echo  Message de commit prevu :
echo ========================================
type "%~dp0commit_message.txt"
echo.
echo ========================================
echo.

set /p ok="[5/6] Continuer avec commit + push ? [o/n] "
if /I not "%ok%"=="o" goto abort

echo.
echo Stage de tous les changements...
git add -A
if errorlevel 1 goto err

echo Commit...
git commit -F "%~dp0commit_message.txt"
if errorlevel 1 goto commit_fail

echo.
echo [6/6] Push vers origin/main...
git push origin main
if errorlevel 1 goto err

echo.
echo ========================================
echo  OK - push termine avec succes.
echo ========================================
echo.
echo N'oublie pas sur ton serveur :
echo     python manage.py migrate
echo     python manage.py loaddata seed_catalog
echo.
goto end

:not_repo
echo ERREUR : le fichier .git est introuvable dans %CD%.
echo Ce script doit etre place dans le dossier racine du projet.
goto end

:commit_fail
echo.
echo ATTENTION : le commit a echoue.
echo Cause possible : rien a committer, ou identite git manquante.
goto end

:err
echo.
echo ========================================
echo  ERREUR - script interrompu.
echo ========================================
goto end

:abort
echo.
echo Annule. Rien n'a ete commit ni push.
echo.

:end
pause
endlocal
