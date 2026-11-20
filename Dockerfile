FROM apache/airflow:3.3.2

# dbt in its own venv, at exactly the versions in uv.lock: the same dbt that CI's slim build runs.
# To upgrade dbt, change pyproject.toml and run `uv lock`; this image follows. (uv comes with the base image.)
COPY --chown=airflow:root pyproject.toml uv.lock /tmp/dbt/
RUN uv export --project /tmp/dbt --frozen --no-dev --no-emit-project --no-hashes -o /tmp/dbt/requirements.txt \
 && python -m venv /home/airflow/dbt-venv \
 && /home/airflow/dbt-venv/bin/pip install --no-cache-dir -r /tmp/dbt/requirements.txt \
 && rm -rf /tmp/dbt

RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" astronomer-cosmos==1.16.0 pytest \
--constraint "${HOME}/constraints.txt"
