FROM amazonlinux:2

RUN mkdir -p /fsx
RUN mkdir -p /efs
RUN mkdir -p /etc/parallelcluster/
RUN echo "cfn_node_type=MasterServer" >> /etc/parallelcluster/cfnconfig
RUN yum install -y sudo hostname wget e2fsprogs systemd
RUN yum install -y python-pip
RUN pip install pytest
RUN wget https://raw.githubusercontent.com/gdraheim/docker-systemctl-replacement/master/files/docker/systemctl.py -O /bin/systemctl && chmod +x /bin/systemctl

WORKDIR /test
COPY ./tests/post-script/test_master.py tests/
COPY ProdPostInstall.py ./tests/

CMD ["pytest"]