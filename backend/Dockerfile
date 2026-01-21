# backend/Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Optimisation : on ne garde pas les fichiers cache de Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Installation des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du reste du code
COPY . .

# Lancement du serveur
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]