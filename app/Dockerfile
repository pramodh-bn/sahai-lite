FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Create non-root user
RUN useradd -m -u 1001 appuser
USER appuser

EXPOSE 8000

CMD ["python", "main.py"]