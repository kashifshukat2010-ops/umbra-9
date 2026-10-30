FROM python:3.12-slim
WORKDIR /app
COPY cyber_assistant_web.py cyber_assistant_cloud.py ./
EXPOSE 7860
CMD ["python", "cyber_assistant_cloud.py"]
