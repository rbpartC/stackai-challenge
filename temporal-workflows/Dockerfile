FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir temporalio pydantic

COPY temporal-workflows/orchestration.py /app/orchestration.py

CMD ["python", "orchestration.py"]