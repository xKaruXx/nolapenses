FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN chmod 0644 /app/app.py /app/requirements.txt && mkdir -p /data && chown -R 1000:1000 /data
USER 1000:1000
EXPOSE 8081
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8081"]
