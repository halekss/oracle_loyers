FROM apache/airflow:2.9.3-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-dev curl && rm -rf /var/lib/apt/lists/*

USER airflow
RUN pip install --no-cache-dir \
    pandas numpy scikit-learn shapely xgboost joblib \
    requests beautifulsoup4
