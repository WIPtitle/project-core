FROM python:3.10

WORKDIR /app
COPY requirements.txt .
COPY . .

COPY entrypoint.sh /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
