FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir mlflow psycopg2-binary boto3

EXPOSE 5000

CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000", "--backend-store-uri", "postgresql+psycopg2://mlflow:mlflow@postgres:5432/mlflow", "--default-artifact-root", "s3://mlflow"]
