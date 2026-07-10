@echo off
cd /d "%~dp0.."
set PYTHONPATH=vendor;%cd%
echo [%date% %time%] Starting Nuitka build in background...
echo Log file: build\nuitka-build.log
echo.
echo [%date% %time%] Starting Nuitka build... > build\nuitka-build.log 2>&1
echo Working directory: %cd% >> build\nuitka-build.log 2>&1
echo PYTHONPATH=%PYTHONPATH% >> build\nuitka-build.log 2>&1
echo. >> build\nuitka-build.log 2>&1

.venv311\Scripts\python.exe -m nuitka ^
    --standalone ^
    --assume-yes-for-downloads ^
    --windows-console-mode=disable ^
    --output-dir=build/nuitka-out ^
    --output-filename=WorkOrderAutomation.exe ^
    --mingw64 ^
    --include-package=customtkinter ^
    --include-package=playwright ^
    --include-package=pandas ^
    --include-package=openpyxl ^
    --include-package=fastapi ^
    --include-package=uvicorn ^
    --include-package=starlette ^
    --include-package=ui ^
    --include-package=config ^
    --include-package=auth ^
    --include-package=pages ^
    --include-package=services ^
    --include-package=core ^
    --include-package=summarize ^
    --include-package=web ^
    --include-module=app ^
    --include-data-dir=data=data ^
    --include-data-dir=web\static=web\static ^
    --include-data-dir=vendor=vendor ^
    --nofollow-import-to=matplotlib ^
    --nofollow-import-to=IPython ^
    --nofollow-import-to=jupyter ^
    --nofollow-import-to=pytest ^
    --nofollow-import-to=scipy ^
    --nofollow-import-to=sklearn ^
    --nofollow-import-to=torch ^
    --nofollow-import-to=tensorflow ^
    --nofollow-import-to=PyQt5 ^
    --nofollow-import-to=PyQt6 ^
    --nofollow-import-to=PySide2 ^
    --nofollow-import-to=PySide6 ^
    --nofollow-import-to=wx ^
    --nofollow-import-to=pandas.tests ^
    --nofollow-import-to=PyInstaller ^
    --nofollow-import-to=playwright._impl.__pyinstaller ^
    run.py >> build\nuitka-build.log 2>&1

echo [%date% %time%] Nuitka build finished with exit code %ERRORLEVEL% >> build\nuitka-build.log 2>&1
echo [%date% %time%] Nuitka build finished with exit code %ERRORLEVEL%

echo [%date% %time%] Copy VC++ runtime DLLs >> build\nuitka-build.log 2>&1
for %%d in (msvcp140.dll msvcp140_1.dll msvcp140_2.dll concrt140.dll) do (
    if exist "%SystemRoot%\System32\%%d" (
        copy /Y "%SystemRoot%\System32\%%d" "build\nuitka-out\run.dist\" >nul
        echo %%d copied >> build\nuitka-build.log 2>&1
    ) else (
        echo WARNING: %%d not found >> build\nuitka-build.log 2>&1
    )
)
echo [%date% %time%] VC++ DLL copy done >> build\nuitka-build.log 2>&1

echo.
echo Check build\nuitka-build.log for details.
