@echo off
rem Demo nhanh: API du bao (FastAPI) + app Flutter ban release tren may ao Android.
rem Lan dau: tao .venv + build APK (~5-15 phut). Cac lan sau: chi mo app, khong build lai
rem tru khi code trong mobile\lib, mobile\assets hoac pubspec.yaml thay doi.
setlocal
cd /d "%~dp0"
set "URL=http://127.0.0.1:8000"
set "AVD=Pixel_10a"
set "PKG=com.example.mobile"
set "ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
set "EMU=%LOCALAPPDATA%\Android\Sdk\emulator\emulator.exe"
set "APK=mobile\build\app\outputs\flutter-apk\app-release.apk"
set "STAMP=mobile\build\.installed_release"
set "FLUTTER=flutter"
where flutter >nul 2>nul || set "FLUTTER=D:\flutter\bin\flutter.bat"

rem --- 1. Bat may ao truoc (buoc lau nhat), chay song song voi cac buoc sau ---
"%ADB%" get-state >nul 2>nul
if errorlevel 1 (
    echo [1/5] Bat may ao %AVD%...
    start "" "%EMU%" -avd %AVD% -no-boot-anim
) else (
    echo [1/5] May ao da chay san.
)

rem --- 2. Moi truong Python (chi lan dau) ---
if not exist ".venv\.installed" (
    echo [2/5] Tao moi truong Python va cai thu vien...
    if not exist ".venv\Scripts\python.exe" python -m venv .venv || goto :fail
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :fail
    echo ok> ".venv\.installed"
)

rem --- 3. Bat API (thu nho cua so) ---
curl -s -o nul %URL%/docs
if errorlevel 1 (
    echo [3/5] Khoi dong API...
    start "Flood API - dong cua so nay de tat" /min ".venv\Scripts\python.exe" -m uvicorn ml.src.models.19_live_api:app --host 127.0.0.1 --port 8000
) else (
    echo [3/5] API da chay san.
)

rem --- 4. Build APK release chi khi code thay doi ---
rem shortcut: chi so thoi gian sua file trong lib/assets/pubspec.yaml; sua android/ thi xoa APK de build lai.
powershell -NoProfile -Command "$a='%APK%'; if(!(Test-Path $a)){exit 1}; $t=(Get-Item $a).LastWriteTime; if(Get-ChildItem mobile\lib,mobile\assets,mobile\pubspec.yaml -Recurse -File | Where-Object LastWriteTime -gt $t | Select-Object -First 1){exit 1}; exit 0"
if errorlevel 1 (
    echo [4/5] Build APK release ^(chi build cho may ao x64^)...
    pushd mobile
    call "%FLUTTER%" build apk --release --target-platform android-x64 || (popd & goto :fail)
    rem Tat Gradle daemon de tra ~800MB RAM cho may ao.
    call android\gradlew.bat --stop >nul 2>nul
    popd
    if exist "%STAMP%" del "%STAMP%"
) else (
    echo [4/5] APK da moi nhat, bo qua build.
)

rem --- 5. Doi may ao, cai app neu can, mo app ---
echo [5/5] Doi may ao khoi dong xong...
"%ADB%" wait-for-device
"%ADB%" shell "while [ -z $(getprop sys.boot_completed) ]; do sleep 1; done"
set "NEED_INSTALL="
if not exist "%STAMP%" set NEED_INSTALL=1
"%ADB%" shell pm path %PKG% >nul 2>nul || set NEED_INSTALL=1
if defined NEED_INSTALL (
    echo       Cai app len may ao...
    "%ADB%" install -r "%APK%" || goto :fail
    echo ok> "%STAMP%"
)
"%ADB%" shell am start -n %PKG%/.MainActivity >nul

set /a TRIES=0
:wait_api
curl -s -o nul %URL%/docs && (start "" "%URL%/docs" & goto :api_ok)
set /a TRIES+=1
if %TRIES% lss 30 ("%SystemRoot%\System32\timeout.exe" /t 1 >nul & goto :wait_api)
echo Canh bao: API chua len, xem cua so "Flood API".
:api_ok

echo.
echo Xong. App dang mo tren may ao, API o %URL%/docs
echo Dong cua so "Flood API" de tat server. Can sua code co hot reload: cd mobile ^&^& flutter run
"%SystemRoot%\System32\timeout.exe" /t 8
exit /b 0

:fail
echo Loi - xem thong bao phia tren.
pause
exit /b 1
