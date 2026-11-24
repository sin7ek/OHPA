FROM python:3.12-slim AS runtime
LABEL org.opencontainers.image.source="https://github.com/sin7ek/open-heatpump-analytics"
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

FROM runtime AS standalone
