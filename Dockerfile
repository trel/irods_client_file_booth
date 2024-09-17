FROM python:3.12

RUN pip install cherrypy python-irodsclient

COPY app.css /
COPY app.py /

ENTRYPOINT ["python", "app.py"]
