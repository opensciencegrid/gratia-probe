FROM almalinux:9

ARG TIMESTAMP_IMAGE=gratia-probe-k8s:release-$(date +%Y%m%d-%H%M)
ARG OSG_SERIES=24
ENV GRATIA_PROBE_VERSION=$TIMESTAMP_IMAGE
ARG UID=10000
ARG GID=10000

# Install EPEL, the OSG software base repo, and gratia-probe-common
RUN yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm && \
    yum install -y https://repo.osg-htc.org/osg/$OSG_SERIES-main/osg-$OSG_SERIES-main-el9-release-latest.rpm && \
    yum install -y gratia-probe-common python3-pip

# Make probe runnable as non-root
RUN chown -R $UID:$GID /var/lock/gratia /var/lib/gratia/data /var/lib/gratia/tmp /var/log/gratia
WORKDIR /gratia
COPY requirements.txt /gratia
RUN pip install -r requirements.txt
COPY ProbeConfig /etc/gratia/kubernetes/
COPY *.py /gratia/

USER $UID:$GID
CMD python3 kubernetes_meter.py
