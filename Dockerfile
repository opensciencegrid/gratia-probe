FROM centos:centos7

RUN yum install -y python3-pip && pip3 install htcondor

COPY . /src/

ENTRYPOINT ["/bin/bash"]
