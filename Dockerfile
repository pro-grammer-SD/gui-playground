# Stage 1: Build environment
FROM python:3.10-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends xvfb x11vnc websockify python3-tk && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime (smaller image)
FROM python:3.10-slim

# Copy installed system binaries from builder
COPY --from=builder /usr/bin/xvfb-run /usr/bin/Xvfb /usr/bin/x11vnc /usr/bin/websockify /usr/bin/
COPY --from=builder /usr/lib /usr/lib
COPY --from=builder /app /app

WORKDIR /app
ENV DISPLAY=:99
ENV PORT=5000
EXPOSE 5000

CMD ["python3", "app.py"]
