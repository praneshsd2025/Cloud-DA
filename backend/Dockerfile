FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && addgroup -S appuser \
    && adduser -S -G appuser appuser

COPY --chown=appuser:appuser app.py /app/
COPY --chown=appuser:appuser test_app.py /app/

USER appuser

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
