@echo off
rem Demo nhanh: API du bao mua lon (FastAPI) + app Flutter (neu may co Flutter).
rem Lan dau chay se tao .venv va cai thu vien (vai phut), cac lan sau chay ngay.
setlocal
cd /d "%~dp0"
set URL=http://127.0.0.1:8000

if not exist ".venv\.installed" (
    echo [1/3] Tao moi truong Python va cai thu vien...
    if not exist ".venv\Scripts\python.exe" python -m venv .venv || goto :fail
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :fail
    echo ok> ".venv\.installed"
)

curl -s -o nul %URL%/docs
if errorlevel 1 (
    echo [2/3] Khoi dong API tai %URL% ...
    start "Flood API - dong cua so nay de tat" ".venv\Scripts\python.exe" -m uvicorn ml.src.models.19_live_api:app --host 127.0.0.1 --port 8000
) else (
    echo [2/3] API da chay san.
)

set /a TRIES=0
:wait
curl -s -o nul %URL%/docs && goto :ready
set /a TRIES+=1
if %TRIES% geq 60 (echo API khong len sau 60 giay, xem cua so "Flood API". & goto :fail)
timeout /t 1 >nul
goto :wait

:ready
echo API san sang. Mo trinh duyet...
start "" "%URL%/docs"
start "" "%URL%/api/v1/rain-proxy/latest"

where flutter >nul 2>nul
if errorlevel 1 (
    echo [3/3] Bo qua app mobile: may chua cai Flutter SDK.
) else (
    echo [3/3] Chay app Flutter tren Chrome...
    start "Flood App" cmd /k "cd /d mobile && flutter pub get && flutter run -d chrome"
)

echo.
echo Xong. Dong cua so "Flood API" de tat server.
pause
exit /b 0

:fail
echo Loi - xem thong bao phia tren.
pause
exit /b 1
