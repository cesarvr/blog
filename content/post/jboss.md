---
title: "Deploying a WAR on EAP (Openshift)"
date: 2020-05-07T16:56:19+01:00
draft: true
tags: [openshift, build, cheatsheet]
---


First look for the JBoss EAP image.

<!--more-->

```sh
oc login  ## Get into Openshift
oc project your-project
oc get is -n openshift | grep jboss

#...
#jboss-eap71-openshift  docker-registry.default.svc:5000/openshift/jboss-eap71-openshift 1.2,1.3
#jboss-eap72-openshift  docker-registry.default.svc:5000/openshift/jboss-eap72-openshift ...

```

> ``jboss-eap`` is the oficial JBoss Application server image.


Make a [build configuration](https://docs.openshift.com/container-platform/4.1/builds/understanding-buildconfigs.html) using the image we found above ``jboss-eap71-openshift``.  

```sh
oc new-build jboss-eap72-openshift:latest --name=jboss-server --binary=true
oc get bc

# We should get this...
#NAME           TYPE      FROM      LATEST
#jboss-server   Source    Binary    0
```

## Making The Container

To create the container we need to trigger the build configuration:

```sh
oc start-build bc/jboss-server --from-file=my_war_file.jar --follow
```

> This [build is of type](https://dzone.com/articles/4-ways-to-build-applications-in-openshift-1) ``binary``, it comes handy to create images that will execute binaries or assets (*such as scripts*) that run against the image runtime (like a JVM).

## Deploying The Image

To deploy the image we need to find the [ImageStream](https://docs.openshift.com/enterprise/3.0/architecture/core_concepts/builds_and_image_streams.html):

```sh
oc get is
#jboss-server   docker-registry.default.svc:5000/login/jboss-server

oc create dc jboss-srv --image=docker-registry.default.svc:5000/login/jboss-server
```

> We need to deploy this container from this Docker registry endpoint ``/login/jboss-server``.


### Sending Traffic

For this we need two objects:

A [Service](https://docs.openshift.com/enterprise/3.0/architecture/core_concepts/pods_and_services.html#services):

```sh
oc expose dc/jboss-srv --port=8080
```

> This basically make the container/pod available to the cluster via port ``8080``.

And a [Route](https://docs.openshift.com/container-platform/3.9/dev_guide/routes.html):

```sh
oc expose svc/jboss-srv
oc get route

#             URL
#jboss-srv  jboss-srv.e4ff.pro-eu-west-1.openshiftapps.com
```

> This make it available from your browser as long as they are on the same network.
