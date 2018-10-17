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

Istio is a new framework promising to put some order to your mesh of services, and for me there is not better way to understand how it works than to try to replicate some of its functionalities and more important learn how to use this techniques to create powerful applications. I'll try to separate this article in the three following sections: 

<!--more-->

- How to deploy applications with supporting multiple containers.  
- Develop a simple Decorator/Proxy, this proxy will gather some basic telemetry and application traceability.  
- Write a simple dashboard. This dashboard will allow us to read the distributed telemetry and work as a remote control for our services.  

Before start make sure you the [oc-client](https://github.com/openshift/origin/blob/master/docs/cluster_up_down.md) with oc-cluster-up or even better make a free account in [OpenShift.io](https://manage.openshift.com). If you have trouble understanding some concept just use this [guide to learn the basics](https://github.com/cesarvr/Openshift). 

# Understanding The Pod

We can think of **pods** like a container of containers, they provide a [layer of virtualisation](http://cesarvr.github.io/post/2018-05-22-create-containers/) very similar to the one provided by your typical container provider (like Docker), this mean that containers running inside, share the same resources like memory, cpu time and volumes.

## Anatomy of the Pod 

This is a quick example of a [pod template](https://gist.github.com/cesarvr/3e80053aca02c7ccd014cbdfc2288444):

```yml 
apiVersion: v1
kind: Pod
metadata:
  name: myapp-pod
  labels:
    app: myapp
spec:
  containers:
  - name: myapp-container
    image: busybox
command: ['sh', '-c', 'echo Hello World! && sleep 3600']
```

We are interested in the **containers** section which is the one defining the pods content, here we tell OpenShift to create an image using busybox (a very small Linux distro) and we want to display "echo Hello World" and sleep for 3000 seconds. Pay special attention to this section as we are going to revisit later. 

If you save this in a file called pod.yml, you can feed this template to Kubernetes/OpenShift like this:

```sh
oc create -f pod.yml 

# or you can create using a template stored somewhere else 
oc create -f https://gist.github.com/cesarvr/3e80053aca02c7ccd014cbdfc2288444 
```


# Hello World!

Our next stop in the road to create our "service mesh" is to learn how we can create a pod capable of running multiple containers. First, let's deploy a simple web server application. 

For the application we are going to run a simple Node.js application serving some static HTML:   

```sh
  oc new-app nodejs~https://github.com/cesarvr/demos-webgl
```

This command creates all the [deployment controller and services](https://github.com/cesarvr/Openshift) to run our application, from this [source code](https://github.com/cesarvr/demos-webgl). After this application is deployed the only thing remaining is to create an route.  


To create a route we just need to execute the following: 

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

# Adding Container

Adding a new container is very simple, we just need to modify the configuration in charge of our application deployment:

We need to lookup the available deployment configurations by running this command:

```sh
oc get dc | awk '{print $1}'

NAME
webgl-demos
```

We need to edit this resource (```webgl-demos```):

```sh
#You can setup the editor by editing the variable OC_EDIT (example: export OC_EDIT=vim).

oc edit dc/webgl-demos
```
The deployment configuration is provided in the form of a YAML document, we need to navigate to the **containers** section:

```yaml
containers:
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

It's a little bit messy, but is very the syntax is very similar to the simpler version above.

```yaml
- name: sidecar   
  image: busybox
  command: ["sh", "-c", "sleep 3600"]
```

Here we are going to define our second container, we are going to name it *sidecar*. We just need to add this block immediately below the **containers** section. 

```yaml
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

Now we got two container we save and close our editor and we should got the message ```"deploymentconfig.apps.openshift.io "webgl-demos" edited"```, after this configuration has change the container will get re-deployed.

# Sending Messages

If everything is fine our pod should be running two containers instead of one, now we want to check if the theory holds true and we can really interface somehow with containers running inside the same **pod**, for this we want to login inside the new container (**sidecar**) and test the communication with the web server.

Get the running pods: 

```sh
  oc get pod
```

We got this pod ```webgl-demos-3-md7z4```, now remember we have added a new container before so login to the container inside the pod is not as obvious as to write ```oc rsh webgl-demos-3-md7z4```, we need now to specify the container.


```sh
oc rsh -c sidecar webgl-demos-3-md7z4
```

Finally let see if we can communicate with the other container.

```sh
# This will call send a message to the container with ..
# the webserver asking for the index.html
wget -q0- 0.0.0.0:8080/index.html
#<a href="fire_1">fire_1</a><br><a href="gl_point">gl_point</a><br><a href="stars-1">stars-1</a><br><a href="tunnel-1">tunnel-1</a>

```

Here is the whole process: 

![sidecar-deployment](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/prometheus/sidecar-deployment.gif)

# Sending Messages (FileSystem)

We have proved that our container are able to communicate via Unix sockets, now and for completeness send messages via filesystem. The easiest way is to create an internal pod volume. 

## Volume 

We can do this with [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) but those can work across all pods, instead we are going to use a private volume which is just like a storage which is local to the pod. 

```yml
volumes:
- emptyDir: {}
  name: cache-volume
```

We need to edit again our deployment configuration and jump to the ```containers``` section: 

```yml 
containers:

  - name: sidecar   
    image: busybox
    command: ["sh", "-c", "sleep 3600"]
    volumemounts:
    - mountpath: /tmp
      name: cache-volume

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

volumes:
  - emptyDir: {}
    name: cache-volume
```

Here we defined volumes at the same level of containers, this basically tell us that this particular resource storage is shared globally across containers running inside the pod. But this doesn't mean that our containers will pick up automatically we need to setup mounting points. 

For our *sidecar* container: 

```yml
- name: sidecar   
    image: busybox
    command: ["sh", "-c", "sleep 3600"]
    volumemounts:
    - mountpath: /tmp
      name: cache-volume
``` 

For our *sidecar* container: 

```yml
- image: 172.30.254.23:5000/web-apps/webgl-demos@sha256:....ffff3
  imagePullPolicy: Always
  name: webgl-demos
  volumemounts:
  - mountpath: /tmp
    name: cache-volume
``` 

> If to messy just put the block below the name of each container

We save the changes and it automatically will trigger the deployment. Now our two containers can meet each other in the same folder and same storage the only thing left is to prove it.  


```sh 
 # Write "hello world" inside a file /tmp/hello in the container named hello.
 oc exec -c sidecar demos-webgl-9-hx5q9  -- sh -c "echo hello World > /tmp/hello "


 # Read "hello world" inside a file /tmp/hello in the container named hello.
 oc exec -c demos-webgl demos-webgl-9-hx5q9  -- sh -c "tail /tmp/hello"
```



## Container Patterns 

Here are some ideas on applications using more that one containers: 

- You can divide applications in two containers one container handles the business logic, other container handles the network security. 
- You can encapsulate the networking recovering capabilities (circuit breaker, etc) inside a container you know like Istio.
- I'll try to make an example in the next article, inmagine having a group of services and you can turn on and off certain endpoints. 

For more ideas here is a nice [paper](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/45406.pdf) that was the inspiration behind this post.  



