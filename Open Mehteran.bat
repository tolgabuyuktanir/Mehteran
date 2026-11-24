@echo off
rem Starts the Mehteran web interface on Windows. Double-click this file.
rem The interface runs while this window stays open; to stop it, close the window.
rem Started from inside the zip file (Explorer copies only this file to a temporary folder), the rest is missing:
rem say how to unpack it, in English and in Turkish (plain ASCII, any console code page shows it).
if not exist "%~dp0scripts\mehter.cmd" (
  echo.
  echo Mehteran cannot start from inside the zip file.
  echo Right-click the zip file, choose "Extract All...", then open "Open Mehteran.bat" in the new folder.
  echo.
  echo Mehteran zip dosyasinin icinden baslatilamaz.
  echo Zip dosyasina sag tiklayin, "Tumunu Ayikla..." secin, sonra yeni klasordeki "Open Mehteran.bat" dosyasini acin.
  echo.
  pause
  exit /b 1
)
call "%~dp0scripts\mehter.cmd" ui
pause
