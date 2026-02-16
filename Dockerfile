FROM python:3.12-slim

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY README.md .
COPY src/ src/

# Install dependencies
RUN pip install --no-cache-dir .

# Copy cloud server entry point
COPY cloud_server.py .

# Railway sets PORT env var
ENV PORT=8000
EXPOSE 8000

CMD ["python", "cloud_server.py"]
