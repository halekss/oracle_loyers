FROM apache/airflow:2.8.1-python3.11

USER root

# Installer les dépendances système
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Installer les packages Python nécessaires
RUN pip install --no-cache-dir \
    pandas==2.1.4 \
    folium==0.15.1 \
    requests==2.31.0 \
    beautifulsoup4==4.12.2 \
    openpyxl==3.1.2 \
    apache-airflow-providers-postgres==5.10.0

# Configuration Airflow
ENV AIRFLOW_HOME=/opt/airflow
