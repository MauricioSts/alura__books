@echo off
rem Where's the Duck - sobe tudo no Windows: ambiente Python, build do frontend e o app.
setlocal
cd /d "%~dp0"

where python >nul 2>nul || (echo Python 3.11+ nao encontrado. Instale em python.org e marque "Add to PATH". & pause & exit /b 1)

if not exist ".venv\Scripts\python.exe" (
  echo Criando ambiente virtual...
  python -m venv .venv || (echo Falha ao criar o ambiente virtual. & pause & exit /b 1)
)

echo Conferindo dependencias Python...
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt || (echo Falha ao instalar dependencias. & pause & exit /b 1)

if not exist "frontend\dist\index.html" (
  where npm >nul 2>nul || (echo Node.js nao encontrado. Instale o Node 18+ em nodejs.org para compilar a interface. & pause & exit /b 1)
  echo Compilando a interface...
  pushd frontend
  call npm install --no-audit --no-fund || (popd & echo Falha no npm install. & pause & exit /b 1)
  call npm run build || (popd & echo Falha no build da interface. & pause & exit /b 1)
  popd
)

echo Abrindo o Where's the Duck...
".venv\Scripts\python.exe" -m wheres_the_duck %*
if errorlevel 1 pause
endlocal
