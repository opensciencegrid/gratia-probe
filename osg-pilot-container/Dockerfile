# run from top-level gratia-probe dir with:
#   docker build -f osg-pilot-container/Dockerfile .

FROM opensciencegrid/software-base:fresh

LABEL name="OSG Pilot Container Probe Container"

RUN yum install -y yum-priorities
RUN yum install -y \
    http://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
RUN yum install -y --enablerepo=devops osg-build

COPY . /root/gratia-probe

RUN yum-builddep -y /root/gratia-probe/rpm/gratia-probe.spec

RUN mkdir -p /root/bld/upstream

# ensure uncommitted changes make it into rpm
RUN cd /root/gratia-probe && git config --global user.email "gratiaprobetests"
RUN cd /root/gratia-probe && git config --global user.name "Gratia Probe Tests"
RUN cd /root/gratia-probe && git commit -am "uncommitted local changes" || :

RUN cd \
    && ver=$(awk '/Version:/ {print $2}' gratia-probe/rpm/gratia-probe.spec) \
    && echo type=git url=/root/gratia-probe tag=HEAD \
            tarball=gratia-probe-$ver.tar.gz > bld/upstream/gp.source

RUN osg-build rpmbuild /root/bld

RUN yum install -y /root/bld/_build_results/gratia-probe-*-*-*.rpm

RUN sed -i -e '/SiteName=/s/"Generic site"/"OSG Pilot Container Probe"/' \
           -e '/EnableProbe=/s/"0"/"1"/' \
           /etc/gratia/*/ProbeConfig

