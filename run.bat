@echo off
setlocal
for /f "tokens=2 delims=:." %%c in ('chcp ^<nul') do set "OLDCP=%%c"
set "OLDCP=%OLDCP: =%"
chcp 65001 >nul <nul
cd /d "%~dp0"
set "ACTION=%~1"
set "MENU="
if "%ACTION%"=="" goto menu

:run
if /i "%ACTION%"=="install" goto install
if /i "%ACTION%"=="examples" goto examples
if /i "%ACTION%"=="tool" goto tool
if /i "%ACTION%"=="server" goto server
if /i "%ACTION%"=="test" goto test
echo Неизвестная команда: %ACTION%
echo Использование: run.bat install ^| examples ^| tool ФАЙЛ.ogg ^| server ^| test
goto end

:menu
set "MENU=1"
echo Практическая работа №2, вариант 15: преобразование OGG в MP3
echo.
echo   1 - установить библиотеки из requirements.txt
echo   2 - создать 5 примеров OGG и преобразовать их в MP3
echo   3 - преобразовать свой файл OGG в MP3
echo   4 - запустить сервер HTTP API (остановить: Ctrl+C)
echo   5 - запустить тесты и отчёт о покрытии
echo.
echo Введите номер и нажмите Enter:
set "CHOICE="
chcp %OLDCP% >nul <nul
set /p "CHOICE=> "
chcp 65001 >nul <nul
if "%CHOICE%"=="1" set "ACTION=install"
if "%CHOICE%"=="2" set "ACTION=examples"
if "%CHOICE%"=="3" set "ACTION=tool"
if "%CHOICE%"=="4" set "ACTION=server"
if "%CHOICE%"=="5" set "ACTION=test"
if not "%ACTION%"=="" goto run
echo Нет такого пункта меню: %CHOICE%
goto end

:install
python -m pip install -r requirements.txt
goto end

:examples
python -m src.samples
for %%f in (examples\*.ogg) do (
    python src\tool.py "%%f" > "examples\%%~nf.mp3"
    if errorlevel 1 (
        del "examples\%%~nf.mp3" 2>nul
    ) else (
        echo Готово: %%f -^> examples\%%~nf.mp3
    )
)
goto end

:tool
set "FILE=%~2"
if not "%FILE%"=="" goto tool_run
echo Введите путь к файлу OGG, например examples\1.ogg:
chcp %OLDCP% >nul <nul
set /p "FILE=> "
chcp 65001 >nul <nul

:tool_run
if "%FILE%"=="" (
    echo Файл не указан
    goto end
)
for %%i in ("%FILE%") do set "OUT=%%~dpni.mp3"
python src\tool.py "%FILE%" > "%OUT%"
if errorlevel 1 (
    del "%OUT%" 2>nul
) else (
    echo Готово: %OUT%
)
goto end

:server
python -m src.server
goto end

:test
python -m coverage run -m unittest -v
python -m coverage report
goto end

:end
if defined MENU pause
chcp %OLDCP% >nul <nul
