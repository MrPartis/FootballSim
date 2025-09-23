@echo off

echo ===============================================
echo      Mini Football Game - Quick Build
echo ===============================================
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

echo Building executable with enhanced configuration...
echo.

REM Clean previous builds
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "MiniFootball.spec" del "MiniFootball.spec"

REM Build the executable with enhanced settings
pyinstaller --onefile ^
    --windowed ^
    --name="MiniFootball" ^
    --add-data="assets;assets" ^
    --add-data="*.py;." ^
    --hidden-import="pygame" ^
    --hidden-import="pygame.mixer" ^
    --hidden-import="pygame.font" ^
    --hidden-import="pygame.image" ^
    --hidden-import="PIL" ^
    --hidden-import="PIL.Image" ^
    --collect-all="pygame" ^
    --collect-submodules="PIL" ^
    --exclude-module="tkinter" ^
    --exclude-module="matplotlib" ^
    --exclude-module="numpy" ^
    --noupx ^
    main.py

if errorlevel 1 (
    echo Build failed! Check the output above for errors.
    echo.
    echo Common solutions:
    echo 1. Make sure all dependencies are installed: pip install -r requirements.txt
    echo 2. Try building without --windowed flag to see error messages
    echo 3. Check that assets folder exists and contains required files
    pause
    exit /b 1
)

echo.
echo Build successful! 
echo The executable is located in: dist\MiniFootball.exe
echo.

echo Testing the executable...
echo.

REM Test if the executable exists
if exist "dist\MiniFootball.exe" (
    echo Executable file created successfully!
) else (
    echo Warning: Executable file not found in dist folder.
)

echo.
echo You can distribute the MiniFootball.exe file to run the game on any Windows computer
echo without needing Python installed.
echo.
echo Note: The first run might be slower as Windows extracts the embedded files.
echo.

pause