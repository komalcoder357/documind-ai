@echo off
REM Starts DocuMind AI (backend + frontend) with one double-click. Needs Python 3.10+ and Node.js 18+.
cd /d "%~dp0"
if not exist backend\.venv ( python -m venv backend\.venv || goto :err )
call backend\.venv\Scripts\activate.bat
pip install -q -r backend\requirements-dev.txt || goto :err
pushd backend & alembic upgrade head || goto :err
popd
if not exist frontend\node_modules ( pushd frontend & call npm install || goto :err
popd )
start "DocuMind Backend" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload"
start "DocuMind Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 8 >nul
start http://localhost:5173
echo DocuMind AI is starting. Close the two new windows to stop it.
goto :eof
:err
echo.
echo Setup failed. Read the message above (check Python 3.10+ and Node 18+ are installed).
pause
