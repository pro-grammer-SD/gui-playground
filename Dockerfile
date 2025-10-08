# Stage 1: Build + system deps
FROM python:3.13-slim AS builder

# Install system packages (xvfb, x11vnc, websockify, tk for tkinter, curl for Flet if needed)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        xvfb x11vnc websockify python3-tk git curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Install Python dependencies
RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime (smaller image)
FROM python:3.13-slim

# Copy binaries from builder
COPY --from=builder /usr/bin/Xvfb /usr/bin/x11vnc /usr/bin/websockify /usr/bin/python3 /usr/bin/python3-config /usr/bin/
COPY --from=builder /usr/lib /usr/lib
COPY --from=builder /app /app

WORKDIR /app

# Set environment
ENV DISPLAY=:99
ENV PORT=5000
EXPOSE 5000

# Default command
CMD ["python3", "app.py"]
