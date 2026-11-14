FROM python:3.13-slim
RUN pip install --no-cache-dir dbt-core==1.12.6 dbt-bigquery==1.12.1
WORKDIR /dbt
COPY . .