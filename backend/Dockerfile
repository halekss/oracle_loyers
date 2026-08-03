FROM python:3.12-slim

WORKDIR /app

# Optimisation : on ne garde pas les fichiers cache de Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 1. Copie des requirements et installation
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copie du reste du code
COPY . .

EXPOSE 5000

# Healthcheck natif (fonctionne aussi hors docker-compose, ex. déploiement
# standalone) : lit PORT dynamiquement, comme get_server_port() dans app.py.
HEALTHCHECK --interval=30s --timeout=5s --retries=5 --start-period=20s \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", \"5000\")}/api/health', timeout=3)"

# 3. Lancement du serveur (Flask sur le port 5000)
CMD ["python", "app.py"]