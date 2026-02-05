# API Gateway - multi-stage not required for this small app
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

# Non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080
ENV PORT=8080
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "2", "app:app"]
