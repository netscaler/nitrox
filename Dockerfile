FROM python:2
MAINTAINER Chiradeep Vittal <chiradeep.vittal@citrix.com>
RUN mkdir -p /tmp  
RUN (cd /tmp && wget http://downloadns.citrix.com.edgesuite.net/10902/ns-10.5-58.11-sdk.tar.gz )
RUN (cd /tmp && tar xvzf ns-10.5-58.11-sdk.tar.gz && \
    tar xvzf ns-10.5-58.11-nitro-python.tgz && \
    tar xvf ns_nitro-python_tagma_58_11.tar && \
    cd nitro-python-1.0/ && \
    python setup.py install && \
    cd / && \
    rm -rf /tmp && \
    mkdir -p /usr/src/app)

RUN pip install docker-py

COPY *.py /usr/src/app/

ENTRYPOINT ["python", "/usr/src/app/main.py" ]
