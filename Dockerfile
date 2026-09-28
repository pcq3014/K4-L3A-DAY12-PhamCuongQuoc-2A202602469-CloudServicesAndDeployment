# ═══════════════════════════════════════════════════════════════════
# CP2 — Containerization (production-ready)
#
#   builder : cài dependency vào một virtualenv riêng (/opt/venv)
#   runtime : chỉ copy venv + source, chạy bằng user thường
#
# Build thử: docker build -t day12-agent:prod .
#            docker images day12-agent:prod     # xem dung lượng
# ═══════════════════════════════════════════════════════════════════

# ---------- Stage 1: builder ----------
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Chỉ copy requirements trước để layer cài thư viện được cache
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

RUN groupadd --system app && useradd --system --gid app --no-create-home app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app app ./app
COPY --chown=app:app utils ./utils

USER app

EXPOSE 8000

# slim không có curl → dùng Python có sẵn để gọi /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/health', timeout=3)" || exit 1

# Dạng shell để $PORT do cloud gán được nội suy; exec để uvicorn là PID 1 và nhận SIGTERM.
# --timeout-graceful-shutdown: chờ tối đa 20s cho request đang chạy, dưới mức ~30s
#   mà orchestrator đợi trước khi SIGKILL.
# --proxy-headers: tin X-Forwarded-* từ load balancer của platform (HTTPS, IP thật).
# --no-access-log: middleware access_log đã ghi mỗi request thành một dòng JSON.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-graceful-shutdown 20 --proxy-headers --forwarded-allow-ips '*' --no-access-log"]
