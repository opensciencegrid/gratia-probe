# run from top-level gratia-probe dir with:
#   docker build -f osg-pilot-container/Dockerfile .

FROM opensciencegrid/software-base:fresh

LABEL name="OSG Pilot Container Probe Container"

RUN yum install -y --enablerepo=devops osg-build

COPY . /root/gratia-probe

RUN yum-builddep -y /root/gratia-probe/rpm/gratia-probe.spec

RUN mkdir -p /root/bld/upstream

# ensure uncommitted changes make it into rpm
WORKDIR /root/gratia-probe
RUN git config --global user.email "gratiaprobetests"
RUN git config --global user.name "Gratia Probe Tests"
RUN git commit -am "uncommitted local changes" || :

# set up local osg-build rpmbuild
WORKDIR /root
RUN ver=$(awk '/Version:/ {print $2}' gratia-probe/rpm/gratia-probe.spec) \
    && echo type=git url=/root/gratia-probe tag=HEAD \
            tarball=gratia-probe-$ver.tar.gz > bld/upstream/gp.source

RUN osg-build rpmbuild /root/bld

# install probe rpms
RUN yum install -y /root/bld/_build_results/gratia-probe-{osg-pilot-container,common}-*-*.rpm

# do minimal probe configuration
RUN sed -i -e '/SiteName=/s/"Generic site"/"OSG Pilot Container Probe"/' \
           -e '/EnableProbe=/s/"0"/"1"/' \
           /etc/gratia/*/ProbeConfig

# enable the gratia-probes-cron service
RUN touch /var/lock/subsys/gratia-probes-cron

