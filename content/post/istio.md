---
title: "Creating Your Own Istio (Part 1)"
date: 2018-09-19T14:30:07+01:00
lastmod: 2018-09-19T14:30:07+01:00
draft: false
keywords: []
description: "How we can add/remove features to existing micro-services just by adding/removing containers."
tags: [openshift, container, services, kubernetes ]
categories: [openshift, container, services, kubernetes ]
toc: true
image: https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
---

Let say we have a micro-service exposing some business API and we would like to gather some data about its usage pattern, like how many time the endpoints are being called. One way to solve this require modifying the existing code base adding the wanted behaviour in the form of a class or a set of functions (if functional is your thing), then we re-deploying our service and we are done. 

<!--more-->

After successfully deploying this solution the question now is: *How can we reuse this functionality across all our micro-services ?* One way is to create a re-usable module, but that will require we go through all the projects adding that specific module, which is hard work (testing, compatibility, etc.), let's see if we can find a more elegant way to do this.  


# Separating Of Concerns

Other solution can be to separate the new functionality into it's own container. That new container add this functionality to the whole application, and it should do it without modifying the underlying service. This has some advantages, one is, we don't care about the programming language behind the service as long as we use the same protocol and all further enhancements are local to each applications.


But how we can create container like this? That's the answer this posts try to respond, pretty much like **Istio** or <put-here-your-service-mesh>, we are going to try to define a set of "plug and play" behaviour to existing applications. The objective is to learn how to achieve some of the functionalities provided by Istio, so in the future you can replace this functionalities with some real flexible solutions.

## Simple Use Case Scenario  

Here goes one example, imagine you want to enforce some OAuth across all your services, you can write an "Ambassador" container that take care of that on behalf of your services and you are done. If you want to change the security protocol ? You change the code in one place, and re-deploy.

# Before We Start

This guide will be divide in three parts:

- **Part One**: How to deploy applications that runs in multiple containers.  
- **Part Two**: We are going to develop a reusable "Telemetry" container, to gather information about other services.  
- **Part Three**: Write a simple dashboard. Once this "Telemetry" container is appended to other services, we are going to signal our dashboard with the usage information across our "service mesh".   

I'm going to use OpenShift because is the Kubernetes distro I'm most familiar with, but this techniques should also work in Kubernetes as well.

If you want to follow this guide you can install [oc-client](https://github.com/openshift/origin/blob/master/docs/cluster_up_down.md) with oc-cluster-up or even better make a free account in [OpenShift.io](https://manage.openshift.com). If you have trouble understanding some of the concepts, you read this [OpenShift getting started guide](https://github.com/cesarvr/Openshift).


# Understanding The Pod

Pods are the building blocks to create applications in OpenShift, but for our purposes we can think of them as an container of containers, they provide a [isolation layer](http://cesarvr.github.io/post/2018-05-22-create-containers/) similar to Linux container. This means that containers running inside the pods believe they are running in a single machine.   

Like processes running in a "single machine", contained processes can communicate between each other using some of the mechanism we can find in a Unix/Linux environment like System V semaphore, POSIX shared memory or Linux sockets.  

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

This YAML template defines a pod named *my-pod*, inside we are going to deploy a container using busybox (a very small Linux distribution) base image. Then we are going display "Hello World" and sleep to keep the entire container alive for 3 thousand seconds.

We save this in a file called pod.yml and we execute the following command:

```sh
oc create -f pod.yml

# or you can create using a template stored somewhere else
oc create -f https://gist.githubusercontent.com/cesarvr/3e80053aca02c7ccd014cbdfc2288444/raw/52cde49116a6d6261a1f813034b957058180a7ee/pod.yml
```

That template creates the big jail (the pod) and once created it execute inside something similar to this: ```docker run -it busybox echo Hello World!; sleep 3600```.    

We can login into the pods running container using this *magic words*:

```sh
oc rsh my-pod
```

# How To Add More Containers 

Adding a new container to existing pod is not difficult, we just need add a new entry in the template:

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

As you can observe that containers section is a collection, you can add as many containers as you want. After editing our template we just need to load the new template into OpenShift.

```sh
# if you create a pod before, you need to deleted first.
oc delete pod my-pod

# create it again.
oc create -f pod.yml

#or

oc create -f https://gist.githubusercontent.com/cesarvr/97a0139ca2dba9412254d9919da64e69/raw/5e593a9a4b9fff9af06c53670f939fd9caef94ff/pod.yml
```

Logging into the pod gets a bit trickier now as we need to specify the container, let say we want to login into the ```first-container``` container:

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
# the web-server asking for the index.html
wget -q0- 0.0.0.0:8080/index.html
#<a href="fire_1">fire_1</a><br><a href="gl_point">gl_point</a><br><a href="stars-1">stars-1</a><br><a href="tunnel-1">tunnel-1</a>

```

Here is the whole process:

![sidecar-deployment](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/prometheus/sidecar-deployment.gif)


## Container Patterns

By now we should be able to create applications with multiple containers, also another important point is that we demonstrate that containers running inside the pod share the same network. Keep this in mind as we are going to use this in the next article to create our “Telemetry” container to collect information about the usage of the website we deployed earlier. 

If you want to know more about the container patterns you can take a look a this [paper](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/45406.pdf). 
