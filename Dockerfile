FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

# Copy cloud server entry point
COPY cloud_server.py .

# Railway sets PORT env var
ENV PORT=8000
EXPOSE 8000

CMD ["python", "cloud_server.py"]
