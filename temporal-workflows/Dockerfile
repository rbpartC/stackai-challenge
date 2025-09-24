FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir temporalio pydantic

COPY temporal-workflows/orchestration.py /app/orchestration.py
COPY temporal-workflows/client.py /app/client.py
COPY temporal-workflows/worker.py /app/worker.py

CMD ["python", "worker.py"]