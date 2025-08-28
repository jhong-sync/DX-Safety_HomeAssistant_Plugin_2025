# Supervisor가 주입하는 BUILD_ARCH를 사용해 자동 매칭
ARG BUILD_FROM=ghcr.io/home-assistant/${BUILD_ARCH}-base:latest
FROM ${BUILD_FROM}

# 런타임 기본 설정
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 비루트 사용자
RUN adduser -D -H -u 1000 appuser

# 파이썬 & venv 준비
RUN apk add --no-cache python3 py3-pip

# ---- PEP 668 회피: venv 생성 ----
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# (빌드 시 C 확장 필요시 주석 해제)
# RUN apk add --no-cache --virtual .build-deps \
#     build-base python3-dev libffi-dev openssl-dev musl-dev

# 파이썬 의존성
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r /tmp/requirements.txt

# (빌드 의존성 제거)
# RUN apk del .build-deps

# 애드온 파일
WORKDIR /opt/app
COPY app /opt/app/app
COPY run.sh /opt/app/run.sh

# 권한
RUN chmod +x /opt/app/run.sh \
 && chown -R appuser:appuser /opt/app /opt/venv

# Ingress만 쓸 거면 EXPOSE 불필요(있어도 무해)
# EXPOSE 8099

USER appuser

# 읽기전용 루트는 Supervisor가 관리 / data는 rw
CMD ["/opt/app/run.sh"]
