FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y libssl-dev ca-certificates \
    && pip install --upgrade pip certifi \
    && pip install -r requirements.txt

EXPOSE 5000

CMD ["python3", "main.py"]
