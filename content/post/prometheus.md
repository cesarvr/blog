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

Some days ago I was having some fun writing my WebGL graphics API, when I decide it was time to do some demos. I always like to run some complicated stuff and see how they perform and then do benchmarks like iOS vs Android, etc. And because of that I want those demos to be available in the cloud. I choose to the OpenShift instance because is easier for me.  

<!--more-->

To share the demos I though to do the minimum work as possible, so I decide to setup a container with a dumb server using Python SimpleHTTPServer module (I don’t expect a high volume of traffic) and some statics files with the HTML/CSS/Javascript demos and run the container on OpenShift, because I very familiar with the environment and also because I have a free account.

To deploy my simple server I used this template:  

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

This template just create a **pod** called *python-pod* using Python base image from the OpenShift catalog. This image includes the Python 3 interpreter needed to run the SimpleHTTPServer module.  

Here is the command section in more detail:

```sh
cd /tmp/    
```
The Python image ( from the OpenShift catalog ) drops the privilege for almost all folders but ```/tmp```, this is because they recommend to use this image with S2I, but for now that folder its all what I need.

```sh
 git clone https://github.com/cesarvr/demos-webgl demos  
```
Clone the website and save it inside a folder called demos.

```sh
# actual folder /tmp/
cd demos/static/     
python -m http.server 8080   
```
Jump into the static sub-folder and run the Python server module, if you want a closer look to the folder structure you can found it in this [repository.](https://github.com/cesarvr/demos-webgl)

Save this template as ```python.yml``` and run using:

```sh
oc create -f python.yml

# or this way it will pick the template from the github.gist.
oc create -f https://gist.githubusercontent.com/cesarvr/b1ce3b5098292fd01b42b13697301b17/raw/2e730e761b7ac99ac6b8186caac1f0c31e10063f/python.yml
```

Voila!, in just a few seconds the web server should be running in our cluster.

Now let's send some traffic:

```sh
 oc create service loadbalancer python-pod --tcp=8080:8080
```

The service object by default send traffic to the pods with label ``` app: <name-of-your-pods> ```, creating the service with the same name as the pod give us the tag we want.

```yml
selector:
    app: python-pod
```

Next thing is to expose the service:

```sh
oc expose svc python-pod

oc get route

NAME         HOST/PORT                                                      PATH      SERVICES    
my-service   python-pod-web-apps.7e14.starter-us-west-2.openshiftapps.com             my-service   8080                    None

curl python-pod-web-apps.7e14.starter-us-west-2.openshiftapps.com
# HTML from the static site...
```

Now the website [available](http://my-service-web-apps.7e14.starter-us-west-2.openshiftapps.com/).

If you never hear before the concept of pod, service or router you can follow this [guide](https://github.com/cesarvr/Openshift) for beginners.


# Enhancing The Web Server

After a few days I started to pay the price of choosing a dumb static web server, because I started to feel like adding more functionalities to the server side, like a visiting counter for each demo for example or how much time it is taking to process a request to debug network problem.

I started thinking about this so called *service meshes* like Istio or Prometheus, the only problem is that my OpenShift account won't give me the account privilege to install any of that. Then I though what if I put another container in front that receive the request take care of the statistic and forward the request to the static web server.

It might seem like a very complex way of adding new behaviour to a existing application but take a look at few advantages:

* It follows the Open/Close principle: Meaning the you don't have to modify the web server container or in a real case the business logic.
  - You want to migrate a group of legacy services that use some deprecated authentication protocol, you can create a container that works as an adapter for that case, avoiding the need to touch the code of those applications.

* Increase re-usability: I can reuse the statistics container with other applications out of the box, I'll demonstrate this in the final article.

* Single responsibility principle: Each container do one thing and do it well, this very good to put multiple teams working in different key functionalities and also if your container follow this rules (like in OOP) you increase reusability.

* Plug and Play: Adding that behavior is a matter of adding or removing the container.

Sounds like a good idea but first I needed to learn how to make containers run side by side and more important how to make sure they can collaborate.

# Side Container

We can think about **pods** like a container of containers, meaning that we can run more than one container inside, and this containers can share resources like network namespace (port mapping) and they can share mounting points (folders).


## Internal Communication

To proof that containers can communicate between each other at **pod** level I decide to run an experiment, I just needed to execute a new container inside the pod.

```yaml
- name: sidecar   
  image: busybox
  command: ["sh", "-c", "sleep 3600"]
```
This block will create a container named *sidecar*, we are going to use a base image from Busybox (Thinking about OOP it sound like a base class) which include a ssh and the sleep command. Then in the command section we are going to execute the sleep command for 36000 seconds, this will keep the image alive, so we can run try some ideas.    

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

The only difference here is that I just added this new container at the bottom.


```sh
oc delete pod python-pod
oc create -f python.yml
```
I re-create the pods applying the template modifications.


## Messaging

First thing I did was to run ```oc describe``` to check if everything was fine:

```sh
python:
  Container ID:  docker://5b410a99310a8474455ea684e0a63a7633b9620b8f44ce534050446e14af0456
  Image:         python
sidecar:
  Container ID:  docker://8c31392e2fb1921e9ce2eb6079aba02b52cda6b7cb221d506b6b683dc2f35c0a
  Image:         docker-registry.default.svc:5000/web-apps/ambassador
```

Here I saw the **pod** having to containers now let see, if they share the same network namespace then I just have to login into the new created container and request the web page using the 8080 port assigned to the *python* container.

```sh
oc rsh -c sidecar python-pod

wget 0.0.0.0:8080
# index.html           100% |****************|
```

It works!, Now the next step is to create the application to handle the request, get the information we want and delegate it to the web server.
