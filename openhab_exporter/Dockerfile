FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY openhab_exporter/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY openhab_exporter /app

CMD ["python", "/app/exporter.py"]

