FROM python:3.12-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY upload_server.py .
EXPOSE 8088
CMD ["flask", "--app", "upload_server", "run", "--host", "0.0.0.0", "--port", "8088"]
