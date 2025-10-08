# Stage 1: Builder
FROM python:3.10-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    xvfb x11vnc websockify python3-tk && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Stage 2: Runtime
FROM python:3.10-slim

# Install minimal runtime deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    xvfb x11vnc websockify python3-tk && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app /app

ENV DISPLAY=:99
ENV PORT=5000

EXPOSE 5000
CMD ["python3", "app.py"]
