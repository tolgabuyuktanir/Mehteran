@echo off
rem Starts Mehteran on Windows: scripts\mehter.cmd <arguments> (for example: ui).
rem It uses Python 3.11 or later when the computer has one. Otherwise it installs uv (no administrator rights)
rem and uv provides a private Python. Same search as scripts\start.cmd, but it runs "python -m mehteran".
setlocal
cd /d "%~dp0.."
set "PY="
py -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul && set "PY=python"
if defined PY goto run_python

set "UV=uv"
where uv >nul 2>nul && goto run_uv
set "UV=%USERPROFILE%\.local\bin\uv.exe"
if exist "%UV%" goto run_uv
echo Python 3.11+ not found. Installing a private Python for Mehteran (uv; no administrator rights)...
echo Python 3.11+ bulunamadi. Mehteran icin ayri bir Python kuruluyor (uv; yonetici izni gerekmez)...
set "UV_NO_MODIFY_PATH=1"
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
if not exist "%UV%" (
  echo Installation failed. Install Python 3.11+ from https://www.python.org/downloads/ and try again.
  echo Kurulum basarisiz. https://www.python.org/downloads/ adresinden Python 3.11+ kurup yeniden deneyin.
  exit /b 1
)

rem "ui" first brings a git copy up to date, as scripts\start.cmd does. The update and the start stand on one line: cmd
rem reads a batch file line by line while it runs, and the update can change this file. No parentheses around %*: an
rem argument with a ")" (a path like C:\Program Files (x86)\a.pdf) would end such a block early.
:run_uv
if /i "%~1"=="ui" "%UV%" run --no-project --python 3.12 python -m pipeline update & "%UV%" run --no-project --python 3.12 python -m mehteran %* & exit /b
"%UV%" run --no-project --python 3.12 python -m mehteran %* & exit /b

:run_python
if /i "%~1"=="ui" %PY% -m pipeline update & %PY% -m mehteran %* & exit /b
%PY% -m mehteran %* & exit /b
