@echo off
echo Building Mini Football Game Executable...
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo Failed to install PyInstaller. Please install manually: pip install pyinstaller
        pause
        exit /b 1
    )
)

echo Building executable...
echo.

REM Build the executable
pyinstaller --onefile --windowed --name="MiniFootball" --add-data="assets;assets" main.py

if errorlevel 1 (
    echo Build failed! Check the output above for errors.
    pause
    exit /b 1
)

echo.
echo Build successful! 
echo The executable is located in: dist\MiniFootball.exe
echo.
echo You can distribute the MiniFootball.exe file to run the game on any Windows computer
echo without needing Python installed.
echo.
pause