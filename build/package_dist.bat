@echo off
cd /d "%~dp0.."
echo ========================================
echo Package Nuitka build output
echo ========================================

set ROOT=%cd%
set NUITKA_OUT=%ROOT%\build\nuitka-out\run.dist
set APP_DIST=%ROOT%\dist\WorkOrderAutomation

echo [1/5] Create dist directory
if exist "%APP_DIST%" rmdir /s /q "%APP_DIST%"
mkdir "%APP_DIST%" 2>nul
echo   OK

echo [2/5] Copy Nuitka output
xcopy /E /I /Y "%NUITKA_OUT%\*" "%APP_DIST%\" >nul
echo   OK

echo [3/5] Copy data dir
if exist "%APP_DIST%\data" rmdir /s /q "%APP_DIST%\data"
mkdir "%APP_DIST%\data" 2>nul
for %%f in ("%ROOT%\data\*") do (
    copy /Y "%%f" "%APP_DIST%\data\" >nul 2>nul
)
echo   OK

echo [4/5] Copy Chromium browser
set BROWSER_SRC=%ROOT%\ms-playwright
if exist "%BROWSER_SRC%" (
    echo   Copy browser directory...
    if exist "%APP_DIST%\ms-playwright" rmdir /s /q "%APP_DIST%\ms-playwright"
    mkdir "%APP_DIST%\ms-playwright" 2>nul
    for /d %%d in ("%BROWSER_SRC%\chromium-*") do (
        echo   Copying %%~nxd
        xcopy /E /I /Y "%%d" "%APP_DIST%\ms-playwright\%%~nxd\" >nul
    )
    if exist "%BROWSER_SRC%\.links" (
        xcopy /E /I /Y "%BROWSER_SRC%\.links" "%APP_DIST%\ms-playwright\.links\" >nul
    )
    echo   OK
) else (
    echo   No ms-playwright found, skip
)

echo [5/6] Copy VC++ runtime DLLs
for %%d in (msvcp140.dll msvcp140_1.dll msvcp140_2.dll concrt140.dll) do (
    if exist "%SystemRoot%\System32\%%d" (
        copy /Y "%SystemRoot%\System32\%%d" "%APP_DIST%\" >nul
        echo   %%d copied
    ) else (
        echo   WARNING: %%d not found in System32!
    )
)
echo   OK

echo [6/6] UPX compress
if exist "%ROOT%\upx.exe" (
    echo   Running UPX...
    powershell -ExecutionPolicy Bypass -File build\apply_upx.ps1 -TargetDir "%APP_DIST%"
    echo   OK
) else (
    echo   upx.exe not found, skip
)

echo.
echo ========================================
echo Package complete!
echo Output: %APP_DIST%
echo ========================================
pause
