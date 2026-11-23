@echo off
if "%1"=="install" goto install
if "%1"=="tool" goto tool
if "%1"=="examples" goto examples
if "%1"=="test" goto test
echo Usage: run.bat install ^| tool FILE ^| examples ^| test
exit /b 1

:install
python -m pip install -r requirements.txt
exit /b

:tool
python src\tool.py %2
exit /b

:examples
for %%f in (examples\*.txt) do (
    echo === %%f
    python src\tool.py %%f
)
exit /b

:test
python -m unittest -v
exit /b
