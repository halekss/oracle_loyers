FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# On expose le 5000 (comme ton ancien projet)
EXPOSE 5000

# Lancement sur le port 5000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]