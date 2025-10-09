@echo off
echo.
echo =====================================================
echo   Starting Autonomous App Builder Coordinator
echo =====================================================
echo.
echo Checking if port 5000 is free...
netstat -ano | findstr :5000 >nul
if %errorlevel% equ 0 (
    echo Port 5000 is in use. Attempting to free it...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000') do taskkill /PID %%a /F >nul 2>&1
    timeout /t 2 /nobreak >nul
)

echo Port 5000 is now free.
echo.
echo Starting coordinator...
echo.

REM Ensure .env exists
if not exist .env (
    echo .env file not found. Please run scripts\setup.ps1 first.
    goto :EOF
)

REM Warn if GOOGLE_API_KEY is default placeholder
for /f "usebackq tokens=*" %%A in (".env") do (
  echo %%A | findstr /C:"GOOGLE_API_KEY=your-google-api-key-here" >nul
  if %errorlevel%==0 (
    echo WARNING: GOOGLE_API_KEY not configured in .env
    echo Please edit .env and add your Google Gemini API key
  )
)

cd coordinator
python main.py
