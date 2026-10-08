FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Non-root user for isolation
RUN groupadd -r scanner && useradd -r -g scanner -m -d /home/scanner scanner

# Install Python deps
COPY live-scanner/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the modules this service needs (not full repo)
COPY detection/live_scanner.py detection/
COPY detection/__init__.py detection/
COPY utils/ utils/
COPY config.py .
COPY live-scanner/app.py .

# Chromium is pre-installed in the playwright image
# Switch to non-root user
USER scanner

ENV LIVE_SCAN_TIMEOUT_MS=15000
ENV LIVE_SCAN_MAX_WORKERS=2
ENV LIVE_SCAN_ENABLED=true
ENV LLM_VERDICT_ENABLED=false

EXPOSE 5001

CMD ["python", "app.py"]
