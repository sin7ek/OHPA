FROM python:3.12-slim AS runtime
LABEL org.opencontainers.image.source="https://github.com/sin7ek/OHPA"
LABEL org.opencontainers.image.title="Open HeatPump Analytics"
LABEL org.opencontainers.image.description="Local heat pump analytics for Home Assistant"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && groupadd -g 1000 analytics && useradd -u 1000 -g 1000 -M analytics
ARG OHPA_REVISION=unknown
ENV OHPA_REVISION=${OHPA_REVISION}
LABEL org.opencontainers.image.revision=${OHPA_REVISION}
COPY VERSION ./VERSION
COPY *.py ./
COPY static ./static
RUN mkdir /data && chown 1000:1000 /data
USER 1000:1000
EXPOSE 8095
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8095", "--no-access-log", "--no-proxy-headers"]

# Supervisor-owned /data is mounted as root. Prepare only OHPA database paths,
# then drop to the same unprivileged user as standalone Docker.
FROM runtime AS ha_app
USER root
COPY ha-entrypoint.sh /usr/local/bin/ha-entrypoint
RUN apt-get update && apt-get install -y --no-install-recommends util-linux && rm -rf /var/lib/apt/lists/* && chmod 755 /usr/local/bin/ha-entrypoint
ENTRYPOINT ["/usr/local/bin/ha-entrypoint"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8095", "--no-access-log", "--no-proxy-headers"]

FROM python:3.12-slim AS exporter
LABEL org.opencontainers.image.source="https://github.com/sin7ek/OHPA"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 OHPA_INSTALL_MODE=ha_app DATA_DIR=/data
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends util-linux && rm -rf /var/lib/apt/lists/* && groupadd -g 1000 analytics && useradd -u 1000 -g 1000 -M analytics && mkdir /data
RUN pip install --no-cache-dir fastapi uvicorn httpx numpy tzdata
COPY core.py collector.py profiles.py research_flow.py virtual_flow.py vfm_export.py exporter_app.py ./
COPY exporter ./exporter
COPY exporter-entrypoint.sh /usr/local/bin/exporter-entrypoint
RUN chmod 755 /usr/local/bin/exporter-entrypoint
EXPOSE 8096
ENTRYPOINT ["/usr/local/bin/exporter-entrypoint"]
CMD ["uvicorn","exporter_app:app","--host","0.0.0.0","--port","8096","--no-access-log","--no-proxy-headers"]

FROM runtime AS standalone
