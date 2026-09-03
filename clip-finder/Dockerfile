FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Every visitor supplies their own keys. Without this, a .env that slipped into
# the image would be used for everyone's searches.
ENV REQUIRE_USER_KEY=1

EXPOSE 8000
CMD ["python", "app.py"]
