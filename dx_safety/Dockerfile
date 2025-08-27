ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM $BUILD_FROM

# 비루트 실행자 생성
RUN adduser -D -H -u 1000 appuser

# 파이썬 설치 및 의존성
RUN apk add --no-cache python3 py3-pip
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# 애드온 파일 복사
WORKDIR /opt/app
COPY app /opt/app/app
COPY run.sh /opt/app/run.sh
RUN chmod +x /opt/app/run.sh && chown -R appuser:appuser /opt/app

# 환경변수 설정
ENV PYTHONPATH=/opt/app
ENV PYTHONUNBUFFERED=1

USER appuser
EXPOSE 8099

# 읽기전용 루트 기본, data 볼륨은 rw (Supervisor가 관리)
CMD ["/opt/app/run.sh"]