FROM python:3.12-slim
ENV PYTHONPATH=/app
WORKDIR /app
COPY ./temporal-workflows/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./temporal-workflows/app/ /app/

CMD ["python", "worker.py"]