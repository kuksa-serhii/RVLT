🎤 Realtime Voice Live Translator (RVLT)

Цей проєкт реалізує двосторонній голосовий переклад у реальному часі (Українська $\leftrightarrow$ Англійська) з мінімальною затримкою, використовуючи спеціалізований Azure AI Speech Translator API. Ідеально підходить для важливих дзвінків (Teams, Zoom).

1. Попередня Підготовка (Azure & Python)

Створення Ресурсу Azure: Увійдіть у портал Azure та створіть ресурс Speech Service. Збережіть Ключ (Key) та Регіон (Location/Region).

Налаштування Середовища:

# Створіть віртуальне середовище (рекомендовано)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Встановіть залежності
pip install -r requirements.txt


Конфігурація Ключів: Створіть файл .env та додайте свої дані:

# .env
AZURE_SPEECH_KEY="ВАШ_КЛЮЧ_З_AZURE"
AZURE_SPEECH_REGION="westeurope" # Ваш регіон


2. Налаштування Аудіо Маршрутизації (Windows/Voicemeeter)

Цей етап є критичним для забезпечення двосторонньої роботи. Ми будемо використовувати VB-CABLE Virtual Audio Device (або Voicemeeter) для перенаправлення звуку.

Необхідні Пристрої (як у config.py):

AI Input (Клієнт слухає): CABLE Output (VB-Audio Virtual 

AI Output (Клієнт відтворює): CABLE Input (VB-Audio Virtual C

Ваш Слух: Навушники (2- HD65)

Налаштування Voicemeeter (Обов'язково)

Необхідно, щоб Voicemeeter змішував Аудіо Співрозмовника та Ваш Мікрофон в один канал, який слухає AI, і щоб переклад від AI йшов у віртуальний мікрофон дзвінка.

№

Напрямок

Де налаштувати

Призначення

I.

Teams/Zoom Output

Teams/Zoom Audio Settings (Speaker)

Встановіть на CABLE Input

II.

Teams/Zoom Input

Teams/Zoom Audio Settings (Microphone)

Встановіть на CABLE Input (AI буде говорити сюди)

III.

Voicemeeter Mix (B1)

Віртуальний вихід Voicemeeter (наприклад, B1)

Спрямуйте на CABLE Output (це AI Input Device)

IV.

AI Client Output

(Встановлено у config.py)

Спрямовано на CABLE Input (Це мікрофон Teams/Zoom)

Суть: Всі вхідні аудіо (ваші та співрозмовника) мають бути змішані і надіслані на CABLE Output. Клієнт RVLT слухає цей CABLE Output. Переклад від RVLT надсилається на CABLE Input, який Teams/Zoom використовує як свій мікрофон.

3. Запуск

Переконайтеся, що Voicemeeter налаштований та активний.

Запустіть клієнт:

python -m app.rvlt_client


Почніть розмову. Система автоматично виявить мову і почне перекладати.
