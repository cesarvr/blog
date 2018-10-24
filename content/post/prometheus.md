---
title: "Creating Your Own Istio (Part 1)"
date: 2018-09-19T14:30:07+01:00
lastmod: 2018-09-19T14:30:07+01:00
draft: false
keywords: []
description: "Or how to encapsulate application behaviours in reusable containers."
tags: [openshift, imagestream]
categories: [openshift, webhook]
toc: true
images:
  - https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
---

Let say we have a micro-service exposing some business API and we would like to get gather some data about its usage pattern, like how many time the endpoints are being called.

<!--more-->

One way to solve this require modifying the existing code base and then defining the wanted behaviour in the form of a class or a set of functions (if functional is your thing) and re-deploying our changes. After successfully deploying this solution the question now is, how we can reuse this functionality across all your micro-services ? Even when all the services are written in the same language this can a challenging task.

# Separating Of Concerns

Other solution can be to separate this new functionality into it's own container. That new container will act as a decorator for the whole application, providing this new functionality without modifying the underlying service. This paradigm bring lot of advantages, because we don't care about the programming language behind the service as long as we use the same protocol and in the case there is a change in protocol we just need to update our container.

# Before We Start

But how we can create container like this? That's the objective of this post, we are going to learn how we can encapsulate behaviour in containers and use them to enhance existing applications, pretty much like **Istio** or <put-here-your-service-mesh> does. The objective is to identify what is the magic behind this frameworks, so in case of problems you know what to do. Also because, as we are going to see, we can come up with very powerful patterns.

This guide will be divide in three parts:

- **Part One**: How to deploy applications that runs in multiple containers.  
- **Part Two**: We are going to develop a reusable "Telemetry" container, to gather information about other services.  
- **Part Three**: Write a simple dashboard. Once this "Telemetry" container is appended to other services, we are going to signal our dashboard with the usage information across our "service mesh".   

I'm going to use OpenShift because is the Kubernetes distro I'm most familiar with, but this techniques should also work in Kubernetes as well.

If you want to follow this guide you can install [oc-client](https://github.com/openshift/origin/blob/master/docs/cluster_up_down.md) with oc-cluster-up or even better make a free account in [OpenShift.io](https://manage.openshift.com). If you have trouble understanding some of the concepts, you read this [OpenShift getting started guide](https://github.com/cesarvr/Openshift).


# Understanding The Pod

Pods are the building blocks to create applications in the cluster, but for our purposes we can think of them as an container of containers, they provide a [isolation layer](http://cesarvr.github.io/post/2018-05-22-create-containers/) similar to Linux container. This means that containers running inside believe they are running in a single machine.   

And like processes running in a "single machine", contained processes running inside can communicate between each other using some of the mechanism we can find in a Linux environment like System V semaphore, POSIX shared memory or Linux sockets.

## How It Looks

This is a quick example of what a [pod](https://gist.github.com/cesarvr/3e80053aca02c7ccd014cbdfc2288444) looks like:

```xml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  labels:
    app: my-pod
spec:
  containers:
  - name: my-container
    image: busybox
    command: ['sh', '-c', 'echo Hello World! && sleep 3600']
```

Here we are defining a pod named ```my-pod```, inside we are going to deploy a busybox (a very small Linux distribution) container, once this image is deployed, we are going display "Hello World" and sleep to keep the entire container alive for 3 thousand seconds.

We save this in a file called pod.yml and we execute the following command:

```sh
oc create -f pod.yml

# or you can create using a template stored somewhere else
oc create -f https://gist.githubusercontent.com/cesarvr/3e80053aca02c7ccd014cbdfc2288444/raw/52cde49116a6d6261a1f813034b957058180a7ee/pod.yml
```


The container section of that template is similar to do ```docker run -it busybox echo Hello World!; sleep 3600``` in your machine, only difference is that in the case of OpenShift you container is running in a remote computer.  

We can login into the container by running the following command:

```sh
oc rsh my-pod
```

# More Containers

Adding a new container to existing pod is very simple, we just need add a new entry in the template:

```xml
apiversion: v1
kind: pod
metadata:
  name: my-pod
  labels:
    app: my-pod
spec:
  containers:
  - name: first-container
    image: busybox
    command: ['sh', '-c', 'echo Hello World && sleep 3600']
  - name: second-container
    image: busybox
    command: ['sh', '-c', 'echo Hello World 2 && sleep 3600']
```

We re-create the pod using the same instructions above:


```sh
# if you create a pod before, you need to deleted first.
oc delete pod my-pod

# create it again.
oc create -f pod.yml

#or

oc create -f https://gist.githubusercontent.com/cesarvr/97a0139ca2dba9412254d9919da64e69/raw/5e593a9a4b9fff9af06c53670f939fd9caef94ff/pod.yml
```

Login into the containers gets a little bit trickier as we need to specify what container we want to login, let say we want to login into the ```first-container``` container:

```sh
oc rsh -c first-container my-pod
```

If you want to login into the ```second-container```:

```sh
oc rsh -c second-container my-pod
```

# Communication Between Pods

## Simple Server

By now we should understand all the theory behind how the pod works, so let's put some of it into practice and deploy a simple Node.js static web server.

```sh
  oc new-app nodejs~https://github.com/cesarvr/demos-webgl
```

This [new-app](https://github.com/cesarvr/Openshift#using-the-oc-client) command creates [deployment controller](https://github.com/cesarvr/Openshift#deploy) which are in charge of creating pods that will host our static server, the source code for the static server can be found [here](https://github.com/cesarvr/demos-webgl).   

Only thing missing is to create a [router](https://github.com/cesarvr/Openshift#router) to send outside traffic to our pod:

```sh   
  # First let expose our service to outside traffic
  oc expose svc demos-webgl

  # Check the route and make a request with the browser
  oc get route | awk '{print $2}'

  HOST/PORT
  demos-webgl-web-apps.7e14.starter-us-west-2.openshiftapps.com

  # curl demos-webgl-web-apps.7e14.starter-us-west-2.openshiftapps.com
  # <HTML...
```

## Adding A Container

To add a new container, we just need to modify deployment configuration:

We need to lookup the available deployment configurations by running this command:

```sh
oc get dc | awk '{print $1}'

NAME
webgl-demos
```

We need to edit this resource (```webgl-demos```) using ```oc edit```:

```sh
#You can setup the editor by editing the variable OC_EDIT (example: export OC_EDIT=vim).

oc edit deploymentconfig webgl-demos
```

The deployment configuration is provided in the form of a YAML document, from here we are interested in the  **containers** section:

```xml
containers:
  - image: 172.30.254.23:5000/web-apps/webgl-demos@sha256:....ffff3
    imagePullPolicy: Always
    name: webgl-demos
    ports:
    - containerPort: 8080
      protocol: TCP
    - containerPort: 8443
      protocol: TCP
```

It's a little bit messy, but this syntax should look very familiar, we are going to add the new container just below the ```containers:``` section, this way we avoid mistakes.

```xml
- name: sidecar   
  image: busybox
  command: ["sh", "-c", "sleep 3600"]
```

This is the block we want to add just a simple busybox container, the end result should look like this:

```xml
containers:

  - name: sidecar   
    image: busybox
    command: ["sh", "-c", "sleep 3600"]

  - image: 172.30.254.23:5000/web-apps/webgl-demos@sha256:....ffff3
    imagePullPolicy: Always
    name: webgl-demos
    ports:
    - containerPort: 8080
      protocol: TCP
    - containerPort: 8443
      protocol: TCP
    resources: {}
    terminationMessagePath: /dev/termination-log
    terminationMessagePolicy: File
```

We save the content of our editor and we should see ```deploymentconfig.apps.openshift.io "webgl-demos" edited``` message and just after this our pod will get re-created by the deployment controller.


# Sending Messages

We got two container ```webgl-demos``` running the static server in port 8080 and ```sidecar``` running a sleep process, let see if we can connect to the server container from ```sidecar```.   

Get the running pods:

```sh
oc get pod

oc rsh -c sidecar webgl-demos-3-md7z4
```

Let's communicate using ```localhost```:

```sh
# This will call send a message to the container with ..
# the webserver asking for the index.html
wget -q0- 0.0.0.0:8080/index.html
#<a href="fire_1">fire_1</a><br><a href="gl_point">gl_point</a><br><a href="stars-1">stars-1</a><br><a href="tunnel-1">tunnel-1</a>

```

Here is the whole process:

![sidecar-deployment](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/prometheus/sidecar-deployment.gif)

## Container Patterns

This article went longer than I though, but now you should be able to create applications with multiple containers and how to achieve this using OpenShift.

If you want to know more about the container patterns you can take a look a this [paper](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/45406.pdf). In the next post we are going to write our Ambassador container so we can read some usage pattern on any arbitrary servicez.
