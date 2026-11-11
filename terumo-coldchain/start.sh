#!/bin/sh
envsubst '${PORT}' < /app/nginx.conf.template > /etc/nginx/conf.d/default.conf
uvicorn api:app --host 127.0.0.1 --port 8000 &
streamlit run app.py --server.port 8501 --server.address 127.0.0.1 \
  --server.baseUrlPath dash --server.headless true \
  --server.enableCORS false --server.enableXsrfProtection false &
nginx -g 'daemon off;'