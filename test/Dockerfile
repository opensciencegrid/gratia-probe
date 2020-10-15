FROM centos:centos7

LABEL name="EL7 OSG 3.5 Gratia Probe Test Container"

RUN yum install -y yum-priorities
RUN yum install -y \
    http://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
RUN yum install -y \
    http://repo.opensciencegrid.org/osg/3.5/osg-3.5-el7-release-latest.rpm
RUN yum install -y --enablerepo=devops osg-build
RUN yum install -y --enablerepo=osg-empty slurm

RUN mkdir /root/gratia-probe

RUN git clone --depth=1 https://github.com/opensciencegrid/gratia-probe \
    /root/gratia-probe

RUN yum-builddep -y /root/gratia-probe/rpm/gratia-probe.spec

RUN mkdir -p /root/bld/upstream
RUN cd \
    && ver=$(awk '/Version:/ {print $2}' gratia-probe/rpm/gratia-probe.spec) \
    && echo type=github repo=opensciencegrid/gratia-probe tag=master \
            tarball=gratia-probe-$ver.tar.gz > bld/upstream/gp.source
RUN osg-build rpmbuild /root/bld
RUN yum install -y /root/bld/_build_results/gratia-probe-*-*-*.rpm

