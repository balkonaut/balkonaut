FROM python:3.12-slim
RUN pip install --no-cache-dir paho-mqtt==2.1.0
COPY gx.py /gx.py
CMD ["python", "-u", "/gx.py"]
