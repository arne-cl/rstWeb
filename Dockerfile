# WARNING: DO NOT USE THIS CONTAINER IN PRODUCTION, IT IS INSECURE!
#
# This container will start the 'local' version of rstWeb,
# which doesn't use any authentication. You can use it on your local
# machine, e.g. to work with the rst-workbench, but you shouldn't
# run it on a publicly reachalble server if you store any 'valualble'
# data in rstWeb.

FROM ubuntu:18.04

RUN apt-get update -y && apt-get upgrade -y && \
    apt-get install git python-pip phantomjs elinks wget firefox -y && \
    pip2 install cherrypy routes selenium pexpect pytest requests imagehash

COPY . /opt/rstweb/

# Install geckodriver (for using 'headless' Firefox).
WORKDIR /usr/bin
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz && \
    tar -xvzf geckodriver-v0.24.0-linux64.tar.gz && \
    rm geckodriver-v0.24.0-linux64.tar.gz

# start_local.py is not intended to be run as a server, so we have to change
# its IP address to make it work inside a docker container.
#
# Remove all *.pyc files (incl. those in subdirectories).
# Otherwise, pytest will throw an 'import file mismatch' error.
WORKDIR /opt/rstweb
RUN sed 's/import cherrypy$/import cherrypy; cherrypy.server.socket_host = "0.0.0.0"/g' start_local.py >> start_local_docker.py && \
    find -name '*.pyc' -exec rm {} \;

EXPOSE 8080
ENTRYPOINT ["python"]
CMD ["start_local_docker.py"]
