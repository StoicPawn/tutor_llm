FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-ita tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY studyforge ./studyforge
COPY app.py ./app.py
COPY scripts ./scripts

EXPOSE 8000
CMD ["uvicorn", "studyforge.api:app", "--host", "0.0.0.0", "--port", "8000"]
