@echo off
cls
echo ============================================================
echo    GraphRAG System - Production UI
echo ============================================================
echo.
echo Starting production-grade Streamlit interface...
echo.
echo NEW: Modern, professional UI with:
echo   - Gradient design system
echo   - Animated metrics dashboard
echo   - Enhanced UX throughout
echo.
echo Opening at: http://localhost:8501
echo.
echo Press Ctrl+C to stop the application
echo.
echo ============================================================
echo.

cd /d "%~dp0"
streamlit run app.py

pause
