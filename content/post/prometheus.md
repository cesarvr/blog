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

One of the advantages of running applications on containers aside from running in isolation, is that we can easily can create applications that collaborate between each other. They can collaborate via intranet by making call to other nodes inside the cluster but they can collaborate internally inside the pod.

<!--more-->

The pod is a abstraction in Kubernetes/OpenShift that models a machine from the point of view of the container, this mean that they are some properties that hold true for the containers running inside the pod, like they are able to share resources like filesystem (same PVC) and same network namespaces. This is has great side effects, as we can extend and improve functionality of existing running applications.

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

Good news, this proof that we are able to communicate with the website from within the Pod. Now we just need to develop the program to probe that particular website.  

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




```C++
#include <iostream>
#include "network.h"
#include "pipe.h"
#include "http.h"

int main(){
  Server outside{8080};
  Client website{"localhost", 8087};

  server.waitForConnections([&client](int fd_server){
        auto fd_client = client.establishConnection();

        Tunnel tunnel;

        auto tmm = timming();
        tunnel.from(fd_server)
              .to(fd_client)
              .join();
        });

  return 0;
}
```

It looks prettier than Java!. We the program does is to listen in 8080 port, which is forwarded by the Pod. and connect to the port 8087 which is going belong to the website.

If you are interested in to see the full source code, you can find it in [this Github repository.](https://github.com/cesarvr/side-container/tree/master/cpp).   


![Channel](https://github.com/cesarvr/hugo-blog/blob/master/static/prometheus/read-write.png?raw=true)

I wrote a Channel class to create a "tunnel" between both sockets.



# Implementing the Probe

Implementing the probe using a binary can be challenging for those using [OpenShift.IO](https://console.starter-us-west-2.openshift.com), because they don't allow Docker images. This limitation almost jeopardize my whole experiment, but I found out a solution.

I remember that in Node.js, some modules use native dependencies, so I figure out that the builder image provided by OpenShift should have the necessary build tools.

To know if I can do this, I create a small Pod using Node.js builder image:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nodejs-pod
  labels:
    app: nodejs
spec:
  containers:
  - name: starter   
    image: nodejs
    command: ["sh", "-c", "sleep 3600"]
```

Execute and open a sh connection with the Pod:

```sh
# Running the Pod
oc create -f nodejs.yml


# login
oc rsh nodejs-pod
```

Once I was logged inside the container I started to explore to see if I can find the tooling:

```sh
g++
# g++: fatal error: no input files
# compilation terminated.

make
# make
# make: *** No targets specified and no makefile found.  Stop.
```

Awesome!, I found the tools, now I can build my binary by writing a small shell command:

```sh
curl -L https://github.com/cesarvr/side-container/archive/master.zip -o m.zip
unzip m.zip
cd side-container-master/cpp/
make
./server
```

This script grab the zip file with the project from [Github](https://github.com/cesarvr/side-container/tree/master/cpp), extract and compile into a binary.  

Next step is to write this into the ```python.yml``` template:

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
    command: ["sh", "-c", "cd /tmp/ && git clone https://github.com/cesarvr/demos-webgl demos && cd demos/static/ && python -m http.server 8087"]
    ports:
    - containerPort: 8087
  - name: sidecar   
    image: docker-registry.default.svc:5000/openshift/nodejs
    command: ["sh", "-c", "curl -L https://github.com/cesarvr/side-container/archive/master.zip -o m.zip && unzip m.zip && cd side-container-master/cpp/ &&  make && ./server"]
    ports:
    - containerPort: 8080
```


Look the two containers run side by side in the the OpenShift dashboard.

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/prometheus/sidecar.png)




# Measuring Performance
