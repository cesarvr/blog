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

Some days ago, I was watching this video about Istio in Google I/O and while watching it, I started to think on how to do it or how they achieve this or that feature. So, as an excuse to learn how to build containers that collaborate with each other, I decided to replicate some of the functionalities I saw in that video for fun and at the same time to learn how I can encapsulate behaviour like I usually do with objects, but with containers. 

<!--more-->

A good example of this separation of concerns can be found in the so-called *"service mesh"* frameworks like Istio, Linkdr?, Prometheus, etc. Where you have some application running in a container like a typical Restful web service and you add another container that enhance the functionality of that application. For me it can be thought as the equivalent to an object [decorator](https://en.wikipedia.org/wiki/Decorator_pattern) in object oriented programming.  

To understand how to create this type of applications, I decided to deploy a dumb server and enhance/decorate this server with new functionalities following the open close principle or in other words, which said that our functionality should be open for extention and close for modification. Let's see to what extend this can be achieved with containers. 

But before adding any functionality, first we need to learn how we setup our application to run multiple containers and more important how we can handle communication between the two. 

# Simple Web Server 

We are going to create a dumb web server using Python SimpleHTTPServer module which is a command line tool to serve the content of an arbitrary folder. The purpose of using something like this is to demonstrate how we can enhance later the functionality of this process by appending our "decorator/ambassador" container. 

Usage example:

```sh
 cd ~/some-folder 
 python -m http.server 8080 # Now the content of <some-folder> is available in localhost:8080 
```

## Deploy 

We got the web server, now we need to deploy it into our Kubernetes/OpenShift cluster. The template would look something this: 

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
To run this server we'll use a python base image which come with Python 3. Then we define the command we want to run inside our container, that goes as follow:


```sh
cd /tmp/    
```
Jump to the folder temporal folder, Linux systems offer this directory for temporary files, I'm going to use this one because it doesn't require any priviledge.

```sh
git clone https://github.com/cesarvr/demos-webgl demos  
```
Then I'll clone the static HTML website and save it inside a folder called demos. 

```sh
cd demos/static/     
python -m http.server 8080   
```
Jump into the static sub-folder and run the Python server module, if you want to closer look to the folder structure here is the [repository.](https://github.com/cesarvr/demos-webgl)

We call this template [python.yml](https://gist.github.com/cesarvr/b1ce3b5098292fd01b42b13697301b17) and we feed it to the oc-client like this:

```sh
oc create -f python.yml

# or this way it will pick the template from the github.gist.
oc create -f https://gist.githubusercontent.com/cesarvr/b1ce3b5098292fd01b42b13697301b17/raw/2e730e761b7ac99ac6b8186caac1f0c31e10063f/python.yml
```

Voila!, in just a few seconds our web server should be running in our cluster. Now let's send some traffic, by creating a Service.

```sh
 oc create service loadbalancer python-pod --tcp=8080:8080
```

We create the Service called python-pod, the name match the name of the pod this way the traffic is sended directly to the pod. Only step left is to expose that Service, which mean basically to open it to receive traffic from outside of the cluster.

```sh
oc expose svc python-pod 

oc get route

NAME         HOST/PORT                                                      PATH      SERVICES    
my-service   python-pod-web-apps.7e14.starter-us-west-2.openshiftapps.com             my-service   8080                    None

curl python-pod-web-apps.7e14.starter-us-west-2.openshiftapps.com
# HTML from the static site...
```

If you never hear before the concept of pod, service or router you can follow this [guide](https://github.com/cesarvr/Openshift) for begginers.


# Side Container

## Concepts 

The trick of collaboration between containers is that the **pod** behaves like a container of containers, meaning we can place there more than one container, and containers running inside the pod can share resources like network namespace (port mapping) and they can share mounting points (folders). 


## Containers as objects

In object oriented programming (as concieved by Alan Kay) objects collaborate with each other by what he call messages (also known as methods) : 

```cpp 
Class A { 
 void do_something() {}; 
};

A a; 

# passing a message do_something to A
a.do_something();  # he knows what to do! 

a.clear(); # Fail!
``` 

The question is, can we use the same metaphor with containers ? The answer is why not, but we need a little bit more inmagination. To collaborate with each other we can use (as mentioned above) various methods we can use sockets or the filesystem. So basically right now our Python application (using the object oriented analogy) is accepting messages using the port 8080. 

```sh
oc rsh python-pod # loggin inside our container. 

curl 0.0.0.0:8080/index.html   

#<DOCTYPE...>    
```

Think about it, this is not that different from the object counterpart, we can think of this container as a black box that receive a message ```/GET index.html``` and give us a bunch of strings back. Contiuing with the object oriented analogy we need to study how we communicate each object or container.   

  
# From Theory to Practice

## Adding more containers

To demonstrate how containers can talk to each other inside the *pod*, we are going to add to our existing template a simple container running a shell, this way we can perform some experiments. 

```yaml
- name: sidecar   
  image: busybox
  command: ["sh", "-c", "sleep 3600"]
```
This block will create a container called *sidecar*, we are going to use a base image from busybox (Thinking about OOP again, we can even think of this image as a base class) which include a ssh and the sleep command. Then in the command section we are going to execute the sleep command for 3.6K seconds, this will keep the image alive, so we can run try some ideas.    

Our final template will look something like this:

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

The only difference here is that we just added this new container at the bottom. 


```sh
oc delete pod python-pod
oc create -f python.yml
```
We delete the existing pods, and recreate them with our new template.

### Alternative

You can also save that step by editing the Pod template remotely:

```sh
oc edit pod python-pod
```

## Messaging 

Now that our two containers is running, let see how they share messages. Let's login to our newly created container *sidecar*.

```sh
oc rsh -c sidecar python-pod
```
As mentioned before this two containers share the same network namespace, to send and receive messages from the container running in our same area by just asking something in port 8080.

```sh
wget 0.0.0.0:8080
# index.html           100% |*****************|   504  0:00:00 ETA
```

Nice, this message is comming back from our python server, which is running side-by-side. Now we are ready to develop our decorator/ambassador container. In the next article we are going to write the program to enhance the capabilities of the python server, now that we prove that we can talk to it. 



