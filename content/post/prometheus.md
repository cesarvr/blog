---
title: "Prometheus"
date: 2018-09-19T14:30:07+01:00
lastmod: 2018-09-19T14:30:07+01:00
draft: false
keywords: []
description: ""
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

Have you wonder how you can add functionality to an existing application without modifying an application ? We can do this by applying what Brendan Burns call container patterns. Containers patterns is a way to use multiple containers to isolate different behavior, like we do with object oriented programming, but with instead of using classes we use containers.

This patterns are very useful because you can add functionality to an application without making modification, this mean the business doesn't need to care about what the authentication logic we are using to communicate with some other micro-services or why we cannot separate the business logic from the performance probing.

Also we can have multiple specialize containers to achieve different objectives like for example you have one container fetching content and other container serving content.  

<!--more-->

# Web Server

First thing I needed is to create an application to serve static web pages, this can be done with little effort by writing an OpenShift Pod template.

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

For this to work I need to use the Python image provided by OpenShift, but instead of using this image to do S2I (I don't need to create a new image), I just use the image to make use of the Python interpreter. Next step is to define all the steps to deploy a simple web server, we clone the project, navigate to the static folder and once there execute the Python simple server.

I save this template in a file called ```python.yml``` and passed this template to OpenShift like this:

```sh
 oc create -f python.yml
```

Python simple server is just a convenient module (by no means production ready) to publish the content of the current folder through a HTTP web server, you can try in your machine by running this command in an arbitrary folder.

```sh
 cd my_website/
 python -m http.server 8080

 # Now you can access your site in the browser, http://localhost:8080
```

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

Before creating a Prometheus like probe, I'll start by writing a simple example to show how to create a Pod with multiple containers.  

We are going to revisit our template and we are going to add a new container, if you take a look at the YAML, the containers section is a [collection](https://symfony.com/doc/current/components/yaml/yaml_format.html#collections) data structure, meaning that we just need to a few lines to add a new container:

```yaml
- name: starter   
  image: busybox
  command: ["sh", "-c", "sleep 3600"]
```
We are going to end up with something like this:  

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


Then we need recreate the Pod:

```sh
oc delete pod python-pod

#Wait until it gets deleted, then create a new Pod.
oc create -f python.yml
```

This template creates one Pod with two containers inside python and sidecar.

#### Alternative

You can also edit the template in the cloud by doing:

```sh
oc edit pod python-pod
```

But the cloud version of the template has a lot more meta-data and is a bit difficult to read.


## Testing

Before doing anything else I wanted login into the starter container to check if I'm able to communicate with the website, to do this I've to use a slight variation of the ```oc rsh```.


```sh
oc rsh -c sidecar python-pod
```
Once there, I try to see if I can connect to the port 8080 of the Pod by using wget.

```sh
wget 0.0.0.0:8080
# index.html           100% |*****************|   504  0:00:00 ETA
```

Nice, this is good news, this proof that we are able to communicate with the website from within the Pod. Now we just need to develop the program to probe that particular website.  

## Writing Our Probe

This is what we have done so far:

![pod-1](https://github.com/cesarvr/hugo-blog/blob/master/static/prometheus/pod1.png?raw=true)


This is what we want to do:

![pod-2](https://github.com/cesarvr/hugo-blog/blob/master/static/prometheus/pod2.png?raw=true)

We want to change the port of the website from port 8080 to 8087. So let's do this:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: python-pod
  labels:
    app: python
spec:
  containers:
  - name: python-container
    image: python
    command: ["sh", "-c", "cd /tmp/ && git clone https://github.com/cesarvr/demos-webgl demos && cd demos/static/ && python -m http.server 8087"]
    ports:
    - containerPort: 8087
  - name: starter   
    image: busybox
    command: ["sh", "-c", "sleep 3600"]
```

Then we need to write a program that receive traffic in 8080 and redirect that traffic to 8087. To write the program capable of doing that, our programming language need some library capable of working with TCP/IP. I decide to use C++ because I wanted to learn a bit more about the Unix/Linux network API. But now worries, I hide the ugly implementation details behind some nice interfaces.

If you are interested in to see the full source code, you can find it in [this Github repository.](https://github.com/cesarvr/side-container/tree/master/cpp).   


```C++
#include <iostream>
#include "network.h"
#include "pipe.h"
#include "http.h"

int main(){
  Server outside{8080};
  Client website{"localhost", 8087};

  outside.waitForConnections([&website](int outsideTraffic){
    auto websiteTraffic = website.establishConnection();

    Channel ch{outsideTraffic, websiteTraffic};   // This create a bi-directional tunnel.
  });

  return 0;
}
```

This program is very simple, we prepare the program listen in 8080 port, the port forwarded by the Pod. and the port 8087 which is going belong to the website. That Channel class just read from one socket (the one forwarded by the Pod) and the it send the data to the website.

We need to change the port of the website to 8087:
