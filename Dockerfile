FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    GZ_PORT=7777 \
    GZ_HOST=0.0.0.0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ core/
COPY server/ server/
COPY templates/ templates/
COPY static/ static/
COPY GawdZilla.py VERSION LICENSE ./

RUN mkdir -p /app/data/logs /app/data/backups /app/data/builds /app/data/media

EXPOSE 7777

CMD ["python3", "-m", "server.app"]
