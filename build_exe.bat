@echo off
echo Building Protogen...
call .venv\Scripts\pyinstaller protogen_dash.spec
echo.
echo Done! Executable is in dist\Protogen\
pause
