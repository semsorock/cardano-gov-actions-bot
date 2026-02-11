FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gov_actions_bot.py .
COPY ipfs.py .

CMD ["functions-framework", "--target=hello_http", "--port=8080"]
