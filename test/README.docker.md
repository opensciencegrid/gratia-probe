Testing in Docker
=================

## Building a Docker Image for Testing

From the top-level gratia-probe directory, build the image with:

```
docker build -t gratia-probe-testing -f test/Dockerfile .
```

And run with:

```
docker run -it gratia-probe-testing
```

This will start an interactive session where you can test the installed
gratia probes.

Alternatively, you can mount your working copy into the container, and
test running the probes from there, which will contain any local changes
you make to your repo.

```
$ docker run -v "$PWD":/root/gratia-probe-mount -it gratia-probe-testing
# cd /root/gratia-probe-mount
# cd condor
# ./condor_meter
```

