FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && groupadd -g 1000 analytics && useradd -u 1000 -g 1000 -M analytics
COPY *.py ./
COPY static ./static
RUN mkdir /data && chown 1000:1000 /data
USER 1000:1000
EXPOSE 8095
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8095", "--no-access-log"]
