FROM ubuntu:14.04

COPY crawler.py /src/crawler.py
COPY config.ini /src/config.ini


# Install Python.
RUN \
  apt-get update && \
  apt-get install -y python python-dev python-pip python-virtualenv && \
  rm -rf /var/lib/apt/lists/*

RUN pip install beautifulsoup4

CMD ["python", "src/crawler.py"]