FROM python:3.10-slim

ARG SERVICE_NAME

WORKDIR /app

COPY pyproject.toml .
COPY service/ service/

RUN pip install --no-cache-dir ".[${SERVICE_NAME}]"

# Stream stdout/stderr to terminal without initial buffering
ENV PYTHONUNBUFFERED=1

CMD ["python"] 