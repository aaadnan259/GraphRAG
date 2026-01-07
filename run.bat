@echo off
REM GraphRAG Engine Startup Script for Windows

echo ==========================================
echo    GraphRAG Engine Startup
echo ==========================================
echo.

REM Check if .env file exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Please create a .env file using .env.example as template:
    echo   copy .env.example .env
    echo Then edit .env with your credentials.
    exit /b 1
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet

REM Start the application
echo.
echo Starting GraphRAG Engine...
echo Access the application at: http://localhost:8501
echo.
streamlit run app.py
