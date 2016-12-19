FROM python:3.5-slim

COPY requirements.txt rancher-prom-conf.py /

RUN pip install -r /requirements.txt && \
    chmod +x /prom-rancher-conf.py && \
    mkdir -p /etc/prometheus

ENTRYPOINT ["/rancher-prom-conf.py"]

VOLUME /etc/prometheus
