---
title: "Containers Patterns"
date: 2018-09-19T14:30:07+01:00
lastmod: 2018-09-19T14:30:07+01:00
draft: false
keywords: []
description: "How to separate an application behaviours in multiple reusable containers."
tags: []
categories: []
author: ""

# You can also close(false) or open(true) something for this content.
# P.S. comment can only be closed
comment: false
toc: true
autoCollapseToc: false
# You can also define another contentCopyright. e.g. contentCopyright: "This is another copyright."
contentCopyright: false
reward: false
mathjax: false
---

The Pod is an abstraction in Kubernetes and OpenShift that models a machine, this mean that the containers running inside a Pod share resources like filesystem (same PVC) and network namespaces. We can use multiple containers to isolate various aspect of the applications.


<!--more-->


To illustrate this point I going to write two containers/applications one application will serve a static web pages and the other one will intercept and measure the traffic handle by the first one.


# Web Server

Let's deploy our web server, to make things simpler I'm going to use Python simple server module that basically serves the content of a directory.

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

We need to use the Python image provided by OpenShift, but instead of using this image to do S2I (We don't need to create a new image), I just use the image to use the Python interpreter.

```sh
cd /tmp/
git clone https://github.com/cesarvr/demos-webgl demos
cd demos/static/
python -m http.server 8080
```
In the command section we are just specifying that we want to clone the web page contents from [Github](https://github.com/cesarvr/demos-webgl) and we want to go to the static folder and execute the Python server module.

We save this template in a file called [python.yml](https://gist.github.com/cesarvr/b1ce3b5098292fd01b42b13697301b17) and passed this template to OpenShift like this:

```sh
 oc create -f python.yml

 # or this way it will pick the template from the github.gist.
 oc create -f https://gist.githubusercontent.com/cesarvr/b1ce3b5098292fd01b42b13697301b17/raw/2e730e761b7ac99ac6b8186caac1f0c31e10063f/python.yml
```


## Handling traffic

Once we got our Pod running, we need to start directing traffic, in OpenShift this can be done by setting up a service.

```sh
 oc create service loadbalancer python-pod --tcp=8080:8080
```

Next step we inspect the route and test that container is working properly.

```sh
oc get route
NAME         HOST/PORT                                                      PATH      SERVICES    
my-service   my-service-web-apps.7e14.starter-us-west-2.openshiftapps.com             my-service   8080                    None

curl my-service-web-apps.7e14.starter-us-west-2.openshiftapps.com
# HTML from the static site...
```


# Side Container

Adding more containers to our Pod is very simple, if you take a look at the YAML, the containers section is a [collection](https://symfony.com/doc/current/components/yaml/yaml_format.html#collections) data structure, meaning that we just need to add a new container definition following the same rules.

```yaml
- name: starter   
  image: busybox
  command: ["sh", "-c", "sleep 3600"]
```
This block here will create a Busybox container running a sleep process for 3 thousand seconds, giving us enough time to login and study the Pod more closely.

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

This template creates one Pod with two containers inside python and sidecar.


## Alternative

You can also save that step by editing the Pod template remotely:

```sh
oc edit pod python-pod
```

## Testing

Now that our two containers is running let's login into the new container.


```sh
oc rsh -c sidecar python-pod
```
As mentioned before this two containers share the same network namespace, to proof this hypothesis we can make a call to the port used by the web server.

```sh
wget 0.0.0.0:8080
# index.html           100% |*****************|   504  0:00:00 ETA
```

Now that we can interact with the web server container, we can define a different set of strategies.



# Patterns

## Authentication

![](https://github.com/cesarvr/hugo-blog/blob/master/static/prometheus/auth.png?raw=true)

Here you can create two application by two separated teams one team handle the security side of the application the other handles the business logic. This strategy make sense when you want to isolate the security details from application business rules.

Also by using this method you can reuse the security module for other applications out of the box.


## Sidecar

![](https://github.com/cesarvr/hugo-blog/blob/master/static/prometheus/assets.png?raw=true)

This represent two modules sharing the same filesystem storage, this application can be a web server or content management system, whose content is updated independently from the web server in charge of serving the data.

Also it can be a container collecting server logs and streaming it to storage system.


## Hot Plug

![](https://github.com/cesarvr/hugo-blog/blob/master/static/prometheus/interpreter.png?raw=true)

This is very similar to the Sidecar but instead of asset, but for interpreted languages you can have one container scanning the repository for changes and as soon it detect a new version tag it clones the code to the shared filesystem. The other container detects the change and restart the application.
