FROM python:3.10-slim

WORKDIR /app

# Optimisation : on ne garde pas les fichiers cache de Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 1. Copie des requirements et installation
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copie du reste du code
COPY . .

# 3. Lancement du serveur (Flask sur le port 5000)
CMD ["python", "app.py"]