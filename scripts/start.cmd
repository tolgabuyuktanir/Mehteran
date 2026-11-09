@echo off
rem Starts the application on Windows: scripts\start.cmd <arguments> (for example: ui).
rem It uses Python 3.11 or later when the computer has one. Otherwise it installs uv (no administrator rights)
rem and uv provides a private Python for this application.
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
echo Python 3.11+ not found. Installing a private Python for this application (uv; no administrator rights)...
echo Python 3.11+ bulunamadi. Bu uygulama icin ayri bir Python kuruluyor (uv; yonetici izni gerekmez)...
set "UV_NO_MODIFY_PATH=1"
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
if not exist "%UV%" (
  echo Installation failed. Install Python 3.11+ from https://www.python.org/downloads/ and try again.
  echo Kurulum basarisiz. https://www.python.org/downloads/ adresinden Python 3.11+ kurup yeniden deneyin.
  exit /b 1
)

:run_uv
"%UV%" run --no-project --python 3.12 python -m pipeline %*
exit /b

:run_python
%PY% -m pipeline %*
exit /b
