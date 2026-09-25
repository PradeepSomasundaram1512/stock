FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir google-cloud-storage
COPY dashboard/server.py dashboard/auth.py dashboard/index.html dashboard/login.html dashboard/scoreboard.json ./
CMD ["python", "server.py"]
