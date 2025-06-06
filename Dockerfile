FROM python:3.11-slim 

WORKDIR /app

#dont write .pyc files 
#output text to terminal immediately

ENV PYTHONDONTWRITEBYTECODE=1 
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt 

COPY . .

EXPOSE 8000

CMD ["python", "run.py"]