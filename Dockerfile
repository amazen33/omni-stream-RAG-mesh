FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
ARG PROFILE=main
LABEL org.opencontainers.image.description="omni-stream-RAG-mesh runtime; Python 3.12 baseline (3.12/3.13 supported)"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ANONYMIZED_TELEMETRY=False
ENV OMNI_IMAGE_PROFILE=${PROFILE}
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY requirements.txt requirements-lab.txt ./
RUN python -c "import sys; sys.exit('Supported Python is 3.12 or 3.13; image baseline must remain supported') if sys.version_info[:2] not in ((3, 12), (3, 13)) else None" \
    && case "$PROFILE" in main) lock=requirements.txt ;; lab) lock=requirements-lab.txt ;; *) echo "PROFILE must be main or lab" >&2; exit 1 ;; esac \
    && pip install --require-hashes --no-cache-dir --no-compile -r "$lock" \
    && rm -rf /root/.cache
COPY app ./app
COPY domain ./domain
COPY contexts ./contexts
COPY ops ./ops
RUN chown -R app:app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
