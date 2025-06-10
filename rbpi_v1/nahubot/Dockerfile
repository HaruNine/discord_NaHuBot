# 베이스 이미지
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필수 패키지 설치 (ffmpeg, wget 등)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    libffi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 최신 pip 설치
RUN pip install --upgrade pip

# 코드 복사
COPY . /app

# requirements.txt 복사 및 설치
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# yt-dlp 최신 바이너리 설치 (라즈베리파이/ARM64 호환)
RUN wget -O /usr/local/bin/yt-dlp https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

# 봇 실행
CMD ["python", "code/nahu.py"]
