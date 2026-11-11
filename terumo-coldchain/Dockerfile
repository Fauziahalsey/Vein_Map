FROM python:3.11-slim
RUN apt-get update && apt-get install -y nginx gettext-base && rm -f /etc/nginx/sites-enabled/default && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x start.sh
CMD ["./start.sh"]