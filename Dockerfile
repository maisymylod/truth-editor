FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY truth_editor/ truth_editor/
COPY static/ static/

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn truth_editor.web:app --host 0.0.0.0 --port ${PORT}"]
