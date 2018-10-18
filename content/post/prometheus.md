---
title: "Creating Your Own Istio (Part 1)"
date: 2018-09-19T14:30:07+01:00
lastmod: 2018-09-19T14:30:07+01:00
draft: false
keywords: []
description: "Or how to encapsulate application behaviours in reusable containers."
tags: [openshift, imagestream]
categories: [openshift, build, webhook]
toc: true
images:
  - https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
---

I'll try to introduce you to the art of encapsulating behaviour in multiple containers (like objects in programming languages) and make them co-operate together to develop robust applications. 

<!--more-->

# Separation Of Concerns  

Let say for example you have a web service that handle some typical business and it need some data from a second web service which require a legacy/complex authentication. To integrate this services you have two options: 

- The classic approach is to modify the codebase of the existing service adding a module/class called authentication. 

- You can create re-usable "Authenticate" container that handle the authentication problem and then delegates/forward the business part to the service. 

Here are some advantages of this solution: 

* Reusable: If done well, you can reuse the authenticator container with any other service with those authentication requirements. 
* Isolation: Your application is free from code that don't belong there. 
* The two containers can be develop by separated teams. 

This type of encapsulation is what makes frameworks like Istio so powerful, you can add a new set of behaviours like circuit breakers, telemetry, etc., to your applications without (*hopefully*) making your application aware of their existence, following the [single responsibility principle](https://en.wikipedia.org/wiki/Single_responsibility_principle). 

# Before We Start

In this articles I'll try to reproduce some of the Istio features and some other experimental ideas using this multiple containers paradigm. The content will be organized as follows: 

- How to deploy applications with supporting multiple containers.  
- Develop and deploy a simple "Decorator" container, we are going to plug this container to any service and get back some simple telemetry.  
- Write a simple dashboard. Once the "Decorator" container is deployed we are going to signal our dashboard with information.   

I'm going to use OpenShift because is the Kubernetes distro I'm more familiar with it but this techniques should work in Kubernetes as well. Also before we start make sure you have installed [oc-client](https://github.com/openshift/origin/blob/master/docs/cluster_up_down.md) with oc-cluster-up or even better make a free account in [OpenShift.io](https://manage.openshift.com). If you have trouble understanding some of the concepts, you can use this [OpenShift getting started guide](https://github.com/cesarvr/Openshift). 


# Understanding The Pod

We can think of **pods** like a container of containers, they provide a [layer of virtualisation](http://cesarvr.github.io/post/2018-05-22-create-containers/) very similar to the one provided by your typical Linux container (like Docker). This have some advantages in one hand containers running inside share resources like Memory, CPU time and pod storage. In the other they have more mechanism for inter process communication like they communicating via ```localhost``, as I going to show you demonstrate later.  
      

## Anatomy of the Pod 

This is a quick example of what a [pod definition template](https://gist.github.com/cesarvr/3e80053aca02c7ccd014cbdfc2288444) looks like:

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

Here we are defining a pod named ```my-pod``` and inside we are creating a container using busybox (a very small Linux distro), once this image is deployed it will look for the ```echo``` command and display "Hello World" after that it will sleep for 3000 seconds, this will keep the process and container running.

We save this in a file called pod.yml and we execute the following command:

```sh
oc create -f pod.yml 

# or you can create using a template stored somewhere else 
oc create -f https://gist.githubusercontent.com/cesarvr/3e80053aca02c7ccd014cbdfc2288444/raw/52cde49116a6d6261a1f813034b957058180a7ee/pod.yml 
```

Doing that is similar to do ```docker run -it busybox echo Hello World!; sleep 3600`` with the only difference that in the version above the container is executed in a remote machine.  

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

Login into the containers get a little bit trickier as we need to specify what container we want to login, let say we want to login into the ```first-container``` container: 

```sh
oc rsh -c first-container my-pod 
```

If you want to login into the ```second-container```: 

```sh
oc rsh -c second-container my-pod
```
 

# Communication Between Pods 

## Simple Server 

By now we should understand all the theory behind the how the pod works, so let's put some of this theory to practice and deploy a simple Node.js static web server. 

```sh
  oc new-app nodejs~https://github.com/cesarvr/demos-webgl
```

This command creates [deployment controller](https://github.com/cesarvr/Openshift#deploy) which are in charge of creating pods that will host the our static server, the source code for the static server can be found [here](https://github.com/cesarvr/demos-webgl).   

Only thing missing is to create a [route](https://github.com/cesarvr/Openshift#router) to send outside traffic to our pod: 

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

## New Container 

To add a new container, we just need to modify deployment configuration:

We need to lookup the available deployment configurations by running this command:

```sh
oc get dc | awk '{print $1}'

NAME
webgl-demos
```

We need to edit this resource (```webgl-demos```), for that we can use the ```oc edit```:

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

It's a little bit messy, but this syntax looks very familiar, we are going to add the new container just below the ```containers:``` section, this way we avoid mistakes.

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

This article went longer than I though, but I think now you should now enough to put this knowledge into practise, here are some suggestion where using multiples container can be interesting: 

- You can divide applications in two containers one container handles the business logic, other container handles the network security. 
- You can encapsulate the networking recovering capabilities (circuit breaker, etc) inside a container you know like Istio.

For more ideas here is a nice [paper](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/45406.pdf) that was the inspiration behind this post.  

