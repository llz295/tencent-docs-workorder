@echo off
cd /d "%~dp0.."
set PYTHONPATH=vendor;%~dp0..
.venv311\Scripts\python.exe -m nuitka --standalone --assume-yes-for-downloads --enable-plugin=tk-inter --windows-console-mode=disable --output-dir=build/nuitka-out --output-filename=WorkOrderAutomation.exe --file-version=1.0.0.0 --product-version=1.0.0.0 --mingw64 --include-package=customtkinter --include-package=playwright --include-package=pandas --include-package=openpyxl --include-package=fastapi --include-package=uvicorn --include-package=starlette --include-package=ui --include-package=config --include-package=auth --include-package=pages --include-package=services --include-package=core --include-package=summarize --include-package=web --include-module=app --include-data-dir=data=data --include-data-dir=web\static=web\static --nofollow-import-to=matplotlib --nofollow-import-to=IPython --nofollow-import-to=jupyter --nofollow-import-to=pytest --nofollow-import-to=scipy --nofollow-import-to=sklearn --nofollow-import-to=torch --nofollow-import-to=tensorflow --nofollow-import-to=PyQt5 --nofollow-import-to=PyQt6 --nofollow-import-to=PySide2 --nofollow-import-to=PySide6 --nofollow-import-to=wx --nofollow-import-to=pandas.tests --nofollow-import-to=PyInstaller --nofollow-import-to=playwright._impl.__pyinstaller run.py
echo.
echo Copy VC++ runtime DLLs...
copy "%SystemRoot%\System32\msvcp140.dll" "build\nuitka-out\run.dist\" >nul 2>nul
copy "%SystemRoot%\System32\msvcp140_1.dll" "build\nuitka-out\run.dist\" >nul 2>nul
copy "%SystemRoot%\System32\msvcp140_2.dll" "build\nuitka-out\run.dist\" >nul 2>nul
copy "%SystemRoot%\System32\concrt140.dll" "build\nuitka-out\run.dist\" >nul 2>nul
echo VC++ runtime DLLs copied.
