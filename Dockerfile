FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .
COPY templates/ templates/
COPY docs/ docs/

RUN mkdir -p output

EXPOSE 5001

CMD ["python", "api.py"]