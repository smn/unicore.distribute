FROM ubuntu:14.04
MAINTAINER Simon de Haan <simon@praekeltfoundation.org>
RUN apt-get update && apt-get install -y git-core python python-dev python-distribute python-pip
RUN pip install unicore.distribute
RUN mkdir -p /var/unicore/repos/
WORKDIR /var/unicore/
ADD development.ini /var/unicore/
EXPOSE 6543
CMD pserve development.ini
