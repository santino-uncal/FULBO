@echo off
rem Corre todas las pruebas (tests/). Doble clic y listo.
cd /d "%~dp0"
py -m unittest discover tests
pause
