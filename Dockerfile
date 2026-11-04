FROM apache/airflow:3.3.2

RUN python -m venv /home/airflow/dbt-venv \
 && /home/airflow/dbt-venv/bin/pip install --no-cache-dir dbt-core==1.12.6 dbt-bigquery==1.12.1

RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" astronomer-cosmos==1.16.0 \
    --constraint "${HOME}/constraints.txt"

RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" astronomer-cosmos==1.16.0 pytest \
--constraint "${HOME}/constraints.txt"