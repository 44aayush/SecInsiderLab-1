# IDS image (CLAUDE.md 5.6): BPF object built in a throwaway stage, small runtime with bpftool.
FROM python:3.12-slim AS bpf-build
RUN apt-get update \
    && apt-get install -y --no-install-recommends clang llvm libbpf-dev linux-libc-dev make \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY xdp/lab4_common.h xdp/lab4_xdp.bpf.c xdp/Makefile xdp/
RUN make -C xdp clean all

FROM python:3.12-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends bpftool iproute2 iptables \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pytest==9.2.0
WORKDIR /lab4
COPY script/ script/
COPY web/ web/
COPY tests/ tests/
COPY pytest.ini .
COPY docker/ids_entrypoint.sh /usr/local/bin/ids_entrypoint.sh
COPY --from=bpf-build /src/xdp/lab4_xdp.bpf.o xdp/lab4_xdp.bpf.o
RUN chmod +x /usr/local/bin/ids_entrypoint.sh
ENTRYPOINT ["/usr/local/bin/ids_entrypoint.sh"]
CMD ["python3", "script/webui.py", "--host", "172.28.0.2", "--port", "8080"]
