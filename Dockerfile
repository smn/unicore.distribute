FROM pypy:2-2.5.0
MAINTAINER Simon de Haan <simon@praekeltfoundation.org>
RUN pip install unicore.distribute==1.1.1
RUN mkdir -p /var/unicore/repos/
WORKDIR /var/unicore/
ADD development.ini /var/unicore/
EXPOSE 6543
CMD pserve development.ini
