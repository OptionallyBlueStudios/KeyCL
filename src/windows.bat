@ECHO OFF
CLS
ECHO ===============================
ECHO KeyCL Setup
ECHO ===============================
ECHO 1. Add to search (Start Menu)
ECHO 2. Start on startup
ECHO 3. Install requirements
ECHO 4. Uninstall requirements
ECHO 5. Remove from startup
ECHO 6. Remove from search
ECHO 7. Start script
ECHO 8. Install Python
ECHO.

CHOICE /C 12345678 /M "Enter your choice:"

:: List ERRORLEVELS in decreasing order
IF ERRORLEVEL 8 GOTO InstallPython
IF ERRORLEVEL 7 GOTO StartScript
IF ERRORLEVEL 6 GOTO RemoveSearch
IF ERRORLEVEL 5 GOTO RemoveStartup
IF ERRORLEVEL 4 GOTO UninstallReqs
IF ERRORLEVEL 3 GOTO InstallReqs
IF ERRORLEVEL 2 GOTO AddStartup
IF ERRORLEVEL 1 GOTO AddSearch

:AddSearch
    ECHO Creating Start Menu shortcut...
    powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\KeyCL.lnk');$s.TargetPath='%CD%\main.pyw';$s.WorkingDirectory='%CD%';$s.Save()"
    ECHO Added KeyCL to Start Menu.
    GOTO End

:AddStartup
    ECHO Creating Startup shortcut...
    powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\KeyCL.lnk');$s.TargetPath='%CD%\main.pyw';$s.WorkingDirectory='%CD%';$s.Save()"
    ECHO Added KeyCL to Startup.
    GOTO End

:InstallReqs
    ECHO Installing requirements...
    REM Replace with your pip command
    pip install customtkinter pygame keyboard pystray Pillow requests
    GOTO End

:UninstallReqs
    ECHO Uninstalling requirements...
    REM Replace with your pip uninstall command
    pip uninstall customtkinter pygame keyboard pystray Pillow requests
    GOTO End

:RemoveStartup
    DEL "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\KeyCL.lnk"
    ECHO Removed KeyCL from Startup.
    GOTO End

:RemoveSearch
    DEL "%APPDATA%\Microsoft\Windows\Start Menu\Programs\KeyCL.lnk"
    ECHO Removed KeyCL from Start Menu.
    GOTO End

:StartScript
    ECHO Starting KeyCL...
    START "" "%CD%\main.pyw"
    GOTO End

:InstallPython
    ECHO Opening Python website...
    START https://www.python.org/downloads/
    GOTO End

:End
ECHO.
PAUSE
EXIT