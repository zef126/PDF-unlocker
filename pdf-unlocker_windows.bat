@echo off
cd /d "%~dp0"

if exist "pdf-unlock-env-win\" (
    call pdf-unlock-env-win\Scripts\activate.bat
) else (
    python -m venv pdf-unlock-env-win
    call pdf-unlock-env-win\Scripts\activate.bat
    python -m pip install --upgrade pip --disable-pip-version-check
    pip install -r requirements.txt
)

python Pdf-unlocker.py
pause