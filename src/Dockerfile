FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY DB.csv . 

COPY baml_src/ baml_src/
RUN baml-cli generate

COPY agent.py . 

CMD ["uvicorn", "agent:web_app", "--host", "0.0.0.0", "--port", "8080"]
