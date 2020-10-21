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

