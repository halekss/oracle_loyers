FROM apache/airflow:2.9.3-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-dev curl && rm -rf /var/lib/apt/lists/*

USER airflow
# xgboost épinglé (ORA-152) : cette image tourne en Python 3.11, qui pouvait
# résoudre "xgboost" (non-épinglé) vers une version bien plus récente (3.2.0
# constaté) que celle installable côté backend (Python 3.9 -> XGBoost <= 2.1.4,
# voir backend/requirements.txt). La désérialisation cross-version du pickle
# entraîné ici corrompait les prédictions servies par le backend (loyers
# négatifs) au lieu de simplement avertir. Garder cette version alignée avec
# backend/requirements.txt tant que le backend reste sur Python 3.9.
RUN pip install --no-cache-dir \
    pandas numpy scikit-learn shapely xgboost==2.1.4 joblib \
    requests beautifulsoup4 folium
