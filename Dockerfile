# Используем Python как основной образ
FROM python:3.10.9

# Устанавливаем Node.js и PM2
RUN apt-get update && \
    apt-get install -y curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g pm2

# Переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Рабочая директория
WORKDIR /pm_bot

# Копируем зависимости
COPY requirements.txt .

# Установка зависимостей Python
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# Копируем проект
COPY . .

# Доп. директории
RUN mkdir -p /pm_bot/tables

# Порт
EXPOSE 8000

# Запуск через pm2
CMD ["pm2-runtime", "start", "tg_bot.py", "--interpreter", "python3", "--name", "PM_Bot"]
