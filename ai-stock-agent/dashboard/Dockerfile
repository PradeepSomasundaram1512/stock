FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir google-cloud-storage
COPY dashboard/server.py dashboard/auth.py dashboard/index.html dashboard/login.html dashboard/public.html dashboard/charts.js dashboard/scoreboard.json ./
COPY track_record.py ./verify_chain.py
CMD ["python", "server.py"]
