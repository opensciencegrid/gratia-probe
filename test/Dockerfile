# run from top-level gratia-probe dir with:
#   docker build -f test/Dockerfile .

FROM centos:centos7

LABEL name="EL7 OSG 3.5 Gratia Probe Test Container"

RUN yum install -y yum-priorities
RUN yum install -y \
    http://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
RUN yum install -y \
    http://repo.opensciencegrid.org/osg/3.5/osg-3.5-el7-release-latest.rpm
RUN yum install -y --enablerepo=devops osg-build
RUN yum install -y --enablerepo=osg-empty slurm

COPY . /root/gratia-probe

RUN yum-builddep -y /root/gratia-probe/rpm/gratia-probe.spec

RUN mkdir -p /root/bld/upstream

# ensure uncommitted changes make it into rpm
RUN cd /root/gratia-probe && git add -A && git commit -m autocommit || :

RUN cd \
    && ver=$(awk '/Version:/ {print $2}' gratia-probe/rpm/gratia-probe.spec) \
    && echo type=git url=/root/gratia-probe tag=HEAD \
            tarball=gratia-probe-$ver.tar.gz > bld/upstream/gp.source

RUN osg-build rpmbuild /root/bld

RUN yum install -y /root/bld/_build_results/gratia-probe-*-*-*.rpm

RUN sed -i -e '/SiteName=/s/"Generic site"/"Gratia Probe Docker Tests"/' \
           -e '/Grid=/s/"OSG"/"OSG-ITB"/' \
           -e '/EnableProbe=/s/"0"/"1"/' \
           -e 's/gratia-osg-prod/gratia-osg-itb/g' \
           -e 's/gratia-osg-transfer/gratia-osg-itb/g' \
           /etc/gratia/*/ProbeConfig

