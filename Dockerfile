FROM docker:27-cli AS docker-cli

FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker

WORKDIR /workspace

ENV BUGSINPY_HOME=/workspace/.tools/bugsinpy
ENV PYTHONPATH=/workspace/src

COPY docker-entrypoint.sh /usr/local/bin/apr-entrypoint

RUN chmod +x /usr/local/bin/apr-entrypoint

ENTRYPOINT ["/usr/local/bin/apr-entrypoint"]

CMD ["bash"]
