@echo off
REM Запускає обидва процеси перекладача в окремих вікнах.

echo Starting 🟢 UNDERSTAND process...
START "Translator (Understand EN->UK)" cmd /c "python rvlt_client.py --profile understand"

echo Starting 🟣 ANSWER process...
START "Translator (Answer UK->EN)" cmd /c "python rvlt_client.py --profile answer"

echo Both processes started.