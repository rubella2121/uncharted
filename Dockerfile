# Works on Railway, Fly.io, Koyeb, Google Cloud Run, or any Docker host.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY guard ./guard
COPY data ./data
COPY web ./web
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn guard.api:app --host 0.0.0.0 --port ${PORT} --workers 1"]
