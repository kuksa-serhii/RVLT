@echo off
REM Runs both translator processes and KEEPS windows open on error.
REM This script must be in the ROOT folder (RVLT), not in /app.

echo Starting UNDERSTAND process (EN -> UK)...
REM Runs: python -m app.rvlt_client --profile understand
REM /k KEEPS the window open after the command finishes.
START "Translator (Understand EN->UK)" cmd /k "python -m app.rvlt_client --profile understand"

echo Starting ANSWER process (UK -> EN)...
REM Runs: python -m app.rvlt_client --profile answer
START "Translator (Answer UK->EN)" cmd /k "python -m app.rvlt_client --profile answer"

echo Both processes started.