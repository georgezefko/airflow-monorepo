FROM apache/airflow:3.3.2-python3.12

ARG AIRFLOW_VERSION=3.3.2

# Cosmos LOCAL mode: dbt lives in its own venv so its deps never fight Airflow's constraints.
RUN python -m venv /home/airflow/dbt-venv \
 && /home/airflow/dbt-venv/bin/pip install --no-cache-dir dbt-bigquery==1.12.1

# ponytail: pytest ships in the runtime image so `make test` runs against the real image; split a test stage if image size matters
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" astronomer-cosmos==1.15.1 pytest \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-3.12.txt"
