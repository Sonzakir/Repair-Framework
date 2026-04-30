# See: https://github.com/reproducing-research-projects/BugsInPy
FROM docker.io/continuumio/miniconda3:23.3.1-0

SHELL ["/bin/bash", "-lc"]

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        dos2unix \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN test -f /opt/conda/etc/profile.d/conda.sh \
    && conda --version \
    && python --version


WORKDIR /workspace

ENV PATH="/opt/conda/bin:${PATH}"
ENV BUGSINPY_HOME=/workspace/.tools/bugsinpy
ENV PYTHONPATH=/workspace/src

COPY docker-entrypoint.sh /usr/local/bin/apr-entrypoint

RUN chmod +x /usr/local/bin/apr-entrypoint

ENTRYPOINT ["/usr/local/bin/apr-entrypoint"]

CMD ["bash"]
