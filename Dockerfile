FROM ubuntu:14.04
MAINTAINER Simon de Haan <simon@praekeltfoundation.org>
RUN apt-get update && apt-get install -y git-core python python-dev python-distribute python-pip
RUN pip install unicore.distribute
EXPOSE 6543
