FROM python:3.11-slim

WORKDIR /app

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copie des requirements
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copie du code
COPY . .

# Port d'écoute
EXPOSE 5000

# Commande de démarrage
CMD ["python", "app.py"]