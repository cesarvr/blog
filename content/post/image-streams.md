---
title: "How to work with ImageStreams"
date: 2018-07-31T10:05:23+01:00
lastmod: 2018-07-31T10:05:23+01:00
draft: false
keywords: []
description: ""
tags: [openshift, imagestream]
categories: []
author: ""

# You can also close(false) or open(true) something for this content.
# P.S. comment can only be closed
comment: false
toc: false
autoCollapseToc: false
contentCopyright: false
reward: false
mathjax: false
---

<!--more-->

After you've learn how to build your software and package it into immutable images the next question you may ask is how you deploy it. Deployment of software in OpenShift is handled by an entity called the deployment controller.   


## Creating our image 

Let's create a image builder for a simple Node.js application: 

```
oc new-build nodejs~https://github.com/cesarvr/hello-world-nodejs --name node-build 
``` 

This build published a new image in the image stream called ```node-build```, to deploy it we need to create a deployment controller pointing to its location in the registry. 




```
# the location is in DOCKER REPO   
oc get is

NAME         DOCKER REPO                                           TAGS      UPDATED
node-build   docker-registry.default.svc:5000/hello01/node-build   latest    4 minutes ago

# create deployment controller
oc create dc node-server --image=docker-registry.default.svc:5000/hello01/node-build 

```


To illustrate how it works, we can create a simple [image builder](http://cesarvr.github.io/post/deploy-ocp/) that build and publish images to the image registry. Then we create an image stream that keep track of that image updates. This command ```oc new-build``` will create these two objects.  

```
# creates two objects BuildConfig and ImageStream
oc new-build nodejs~https://github.com/cesarvr/hello-world-nodejs --name node-build

# created BuildConfig
oc get bc
NAME          TYPE      FROM         LATEST
node-build    Source    Git          3


# created ImageStream (both sharing the same name).
oc get is

NAME             DOCKER REPO
node-build       docker-registry.default.svc:5000/hello01/node-build
```   

If your are not familiar with this command (```oc new-build```), it just transform the source code from a git repo into an image. Inside this image the Node.js application is ready to be executed, when it finish then it push the image to the registry. 

This command creates two objects (BuildConfig and Image Stream):

```
  Builder              Container Registry            Image Stream    
+----------+   push   +-------------------+  listen  +----------+  notify
 node-build    -->    ...svc:5000/hello01     <--     node-build    ---> 
+----------+          +-------------------+          +----------+
```


# Deploy

Now that we have our image ready, we want to deploy this image in some node. To deploy an image is very easy first we just need the registry address of the image.

```sh
oc get is

NAME             DOCKER REPO
node-build       docker-registry.default.svc:5000/hello01/node-build
                  ^--- this is the address.


```

Once we know the address we just need to create the DeploymentConfig.     

```
 oc create dc node-ms --image=docker-registry.default.svc:5000/hello01/node-build
```

Our application should be up and running.  

![deployment](https://github.com/cesarvr/hugo-blog/blob/master/static/static/oc-image-stream/oc-deploy-is.gif?raw=true)


# Subscribing

The DeployConfig is unaware of the existence of our image stream it only knows about the image we setup. We need to subscribe our deployment controller using the ```oc set triggers``` command.

```
oc set triggers dc/node-ms --from-image=hello01/node-build:latest -c default-container
```   

This command subscribe *dc/node-ms* deployment to the image stream *hello01/node-build*. If the image stream detect a change it will notify our DeploymentConfig. To test this we just need to publish a new image, starting a new build will do that. 

```
oc start-build bc/node-build --follow
```   

![automatic deployment](https://github.com/cesarvr/hugo-blog/blob/master/static/static/ocp-deploy/ocp-automatic-deploy.gif?raw=true)

We've so far use image stream to automatically deploy our images into a pod, but they are other use cases like triggering BuildConfig's (We can use the [contents of an image to create another image](https://cesarvr.github.io/post/ocp-chainbuild/)) or we can trigger a Jenkin's task that check the container for vulnerabilities, valid signature, etc.
