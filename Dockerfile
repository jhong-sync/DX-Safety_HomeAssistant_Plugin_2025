# Supervisor가 주입하는 BUILD_ARCH 사용
ARG BUILD_FROM=ghcr.io/home-assistant/${BUILD_ARCH}-base:latest
FROM ${BUILD_FROM}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

# python + venv
RUN apk add --no-cache python3 py3-pip \
 && python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip

# 파이썬 의존성 (venv에 설치)
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

# 앱 파일
WORKDIR /opt/app
COPY app /opt/app/app
COPY shelter2025.xlsx /opt/app/share/shelter2025.xlsx
COPY run.sh /opt/app/run.sh
RUN chmod +x /opt/app/run.sh

# Ingress만 사용 → EXPOSE 생략 가능
CMD ["/opt/app/run.sh"]
