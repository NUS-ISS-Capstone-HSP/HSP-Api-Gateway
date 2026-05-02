FROM python:3.12-slim

WORKDIR /srv

RUN pip install --no-cache-dir grpcio protobuf

COPY mock_services/server.py /srv/server.py

EXPOSE 50051

CMD ["python", "/srv/server.py"]
