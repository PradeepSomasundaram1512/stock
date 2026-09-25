FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir google-cloud-storage
COPY dashboard/server.py dashboard/auth.py dashboard/market_clock.py dashboard/sectors.json dashboard/index.html dashboard/login.html dashboard/public.html dashboard/charts.js dashboard/live.js dashboard/manifest.webmanifest dashboard/icon-180.png dashboard/icon-192.png dashboard/icon-512.png dashboard/scoreboard.json ./
COPY track_record.py ./verify_chain.py
CMD ["python", "server.py"]
