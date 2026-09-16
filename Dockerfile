FROM node:20-alpine

RUN apk add --no-cache python3 py3-pip ffmpeg

WORKDIR /app/backend

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt


COPY ytms/ytms /app/backend/ytms/

COPY backend/ /app/backend/

EXPOSE 5001

CMD ["python3", "main.py"]
