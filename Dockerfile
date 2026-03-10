FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

EXPOSE 8089
VOLUME /data

ENV GROCERY_DATABASE_URL=sqlite:////data/grocery.db
ENV GROCERY_UPLOAD_DIR=/data/uploads
ENV GROCERY_SEED_ON_STARTUP=true

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8089"]
