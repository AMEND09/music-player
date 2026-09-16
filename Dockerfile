# Docker Hub is unreachable from some networks, so this builds on the
# widely-cached node:20-alpine image (node also serves as yt-dlp's
# JS runtime) and adds python + ffmpeg on top.
FROM node:20-alpine

RUN apk add --no-cache python3 py3-pip ffmpeg

WORKDIR /app/backend

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY ytms/ /app/ytms/
RUN pip install --no-cache-dir --break-system-packages /app/ytms

COPY backend/ /app/backend/

EXPOSE 5001

CMD ["python3", "main.py"]
