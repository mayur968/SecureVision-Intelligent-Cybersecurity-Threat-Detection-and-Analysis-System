FROM python:3.10-slim

WORKDIR /app

# System deps for python-magic and androguard
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire repo content that the service needs
COPY . .

ENV ML_PORT=5000
ENV ML_ALLOWED_ORIGIN=http://localhost:4000
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
