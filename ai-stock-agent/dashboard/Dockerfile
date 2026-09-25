FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir google-cloud-storage
COPY dashboard/server.py dashboard/index.html ./
CMD ["python", "server.py"]
