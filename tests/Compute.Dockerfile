FROM amazonlinux:2

RUN mkdir -p /fsx
RUN mkdir -p /efs
RUN mkdir -p /etc/parallelcluster/
RUN echo "cfn_node_type=ComputeFleet" >> /etc/parallelcluster/cfnconfig
RUN yum install -y sudo hostname
RUN yum install -y python-pip
RUN pip install pytest

WORKDIR /test
COPY tests/ tests/
COPY ProdPostInstall.py ./tests/

CMD ["pytest"]