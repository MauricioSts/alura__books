@echo off
rem Gera dist\WheresTheDuck.exe (arquivo unico). Requer Python 3.11+ e Node 18+.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" python -m venv .venv || (echo Falha ao criar o ambiente virtual. & pause & exit /b 1)
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt pyinstaller || (echo Falha ao instalar dependencias. & pause & exit /b 1)

pushd frontend
call npm install --no-audit --no-fund || (popd & echo Falha no npm install. & pause & exit /b 1)
call npm run build || (popd & echo Falha no build da interface. & pause & exit /b 1)
popd

".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name WheresTheDuck ^
  --add-data "frontend/dist;frontend/dist" ^
  --collect-submodules uvicorn --collect-submodules websockets --collect-all rapidocr_onnxruntime --collect-binaries onnxruntime ^
  executar.py || (echo Falha ao gerar o executavel. & pause & exit /b 1)

echo.
echo Pronto: dist\WheresTheDuck.exe
pause
endlocal
