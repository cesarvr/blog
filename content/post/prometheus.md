---
title: "Creating Your Own Istio (Part 1)"
date: 2018-09-19T14:30:07+01:00
lastmod: 2018-09-19T14:30:07+01:00
draft: false
keywords: []
description: "Or how to encapsulate application behaviours in reusable containers."
tags: [openshift, imagestream]
categories: [openshift, build, imagestream, webhook]
toc: true
images:
  - https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
---

I just wanted an excuse to write a container oriented application, what do I mean by that? that's not why micro-services are just a bunch of containers talking to one each other. That's true but what I mean is separate different behaviour of an application inside containers and then reuse this containers in other applications.   

<!--more-->

A good example of this separation of concerns are the so-called *"service mesh"* frameworks like Istio, Linkdr?, Prometheus, etc. You add some container to your application and you get some new functionality without affecting (in theory) your application main purpose. They can be thought as the equivalent to an object [decorator](https://en.wikipedia.org/wiki/Decorator_pattern) in object oriented programming.  

To understand how to create this type of applications, I decided to deploy a dumb server and enhance/decorate this server with new functionalities, but I'll follow the open close principle or in other words, without modify or touching the source code. By this I'll reasure the re-usability of both containers. 

But before adding any functionality, first we need to learn how we setup our application to run multiple containers and more important how we can handle communication between the two. 

# Simple Web Server 

We are going to create a dumb web server using Python SimpleHTTPServer module which is a command line tool to serve the content of an arbitrary folder. 

Usage example:

```sh
 cd ~/some-folder 
 python -m http.server 8080 # Now the content of <some-folder> is available in localhost:8080 
```

## Deploy 

Now that we got this web server we can encapsulate it inside a container to run it later in Kubernetes/OpenShift, for this we just need to create a template. 

```sh
apiVersion: v1
kind: Pod
metadata:
  name: python-pod
  labels:
    app: python
spec:
  containers:
  - name: python
    image: python
    command: ["sh", "-c", "cd /tmp/ && git clone https://github.com/cesarvr/demos-webgl demos && cd demos/static/ && python -m http.server 8080"]
    ports:
    - containerPort: 8080
```

This template defines that our container will use python base image, after all we need Python interpreter to run that command. then we define the command we want to run inside our container, that goes as follow:

```sh
cd /tmp/    # jump to the /tmp folder. 
git clone https://github.com/cesarvr/demos-webgl demos  # clone a webpage with some WebGL demos. 
cd demos/static/         # once, cloned jump inside the static folders. 
python -m http.server 8080   # run the python server there. 
```
The content of the Github repository is just a bunch of static HTML pages, if you want to closer look follow this [link](https://github.com/cesarvr/demos-webgl).

We save this template in a file called [python.yml](https://gist.github.com/cesarvr/b1ce3b5098292fd01b42b13697301b17) and passed this template to OpenShift like this:

```sh
oc create -f python.yml

# or this way it will pick the template from the github.gist.
oc create -f https://gist.githubusercontent.com/cesarvr/b1ce3b5098292fd01b42b13697301b17/raw/2e730e761b7ac99ac6b8186caac1f0c31e10063f/python.yml
```

Voila!, in a few seconds our container should be running in our cluster, now let's do some quick configuration to send some traffic, by creating a Service.


```sh
 oc create service loadbalancer python-pod --tcp=8080:8080
```
We create the Service called python-pod, this way it will match our template, this would be enough so it can send traffic to the correct container. Only step left is to expose that Service, which mean basically to open it to receive traffic from outside of the cluster.

```sh
oc expose svc python-pod 

oc get route

NAME         HOST/PORT                                                      PATH      SERVICES    
my-service   python-pod-web-apps.7e14.starter-us-west-2.openshiftapps.com             my-service   8080                    None

curl python-pod-web-apps.7e14.starter-us-west-2.openshiftapps.com
# HTML from the static site...
```

# Side Container

## Concepts 

The trick of collaboration between containers is that the pod behaves like a container of containers, this mean containers running inside the pod can share resources like network namespace (port mapping) and they can share mountin points (folders). 

In object oriented programming (as concieved by Alan Kay) objects collaborate with each other by what he call messages (AKA methods) : 

```cpp 
Class A { 
 void do_something() {}; 
};

A a; 

# passing a message do_something to A
a.do_something();  # he knows what to do! 

a.clear(); # Fail!
``` 

The question is, can we use the same metaphor with containers ? The answer is of course, but we need a little bit more inmagination. To collaborate with each other we can use (as mentioned above) various methods we can use sockets or filesystem. So basically right now our Python application (using the object oriented analogy) is accepting messages using the port 8080. 

```sh
oc rsh python-pod # loggin inside our container. 

curl 0.0.0.0:8080/index.html   

#<DOCTYPE...>    
```

Think about it, this is not that different from the object counterpart, we can think of this container as a black box that receive a message ```/GET index.html``` and give us a bunch of strings back, representing a webpage. Now we need to learn how to communicate two containers inside the same pod.  

  
# From Theory to Practice

## Adding more containers

Adding more containers to our Pod is simple, if you take a look at the YAML, the containers section is a [collection](https://symfony.com/doc/current/components/yaml/yaml_format.html#collections) data structure, meaning that we just need to add a new container definition following the same rules.

We are going to add to our existing template a simple container running a shell, this way we can perform some experimentation while inside. 

```yaml
- name: starter   
  image: busybox
  command: ["sh", "-c", "sleep 3600"]
```
This block here will create a Busybox container running a sleep process for 3000 seconds.

Our template should look something like this:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: python-pod
  labels:
    app: python
spec:
  containers:
  - name: python
    image: python
    command: ["sh", "-c", "cd /tmp/ && git clone https://github.com/cesarvr/demos-webgl demos && cd demos/static/ && python -m http.server 8080"]
    ports:
    - containerPort: 8080
  - name: sidecar   
    image: busybox
    command: ["sh", "-c", "sleep 3600"]
```

We add the line and recreate the Pod:

```sh
oc delete pod python-pod

#Wait until it gets deleted, then create a new Pod.
oc create -f python.yml
```

This template creates one Pod with two containers inside **python** and **sidecar**.

## Alternative

You can also save that step by editing the Pod template remotely:

```sh
oc edit pod python-pod
```

## Testing

Now that our two containers is running let's log in into the new container called *sidecar*.


```sh
oc rsh -c sidecar python-pod
```
As mentioned before this two containers share the same network namespace, to proof this hypothesis we can make a call to the port used by the web server.

```sh
wget 0.0.0.0:8080
# index.html           100% |*****************|   504  0:00:00 ETA
```

This webpage is comming back from our python server container, this is what we wanted. 


Now in the next part we are going to write a program that take that message and do report back what web page the user are visiting, speed and we can even write a dashboard to deactivate a certain endpoint for a specific service/application. 

