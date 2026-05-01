FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DF_PORT=9701

WORKDIR /app

COPY requirements-http.txt ./
RUN pip install --no-cache-dir -r requirements-http.txt

COPY dark_factory_v3 ./dark_factory_v3
COPY paperclip_darkfactory_v3_0_event_contracts.yaml ./
COPY paperclip_darkfactory_v3_0_state_transition_matrix.csv ./
COPY paperclip_darkfactory_v3_0_external_runs.openapi.yaml ./
COPY server.py start_server.sh ./

RUN chmod +x ./start_server.sh && mkdir -p /data

EXPOSE 9701
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9701/api/health', timeout=3).read()" || exit 1

CMD ["./start_server.sh", "--host", "0.0.0.0", "--journal", "/data/dark_factory_v3.jsonl"]
