---
title: "Deploying Applications in Openshift"
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
# You can also define another contentCopyright. e.g. contentCopyright: "This is another copyright."
contentCopyright: false
reward: false
mathjax: false
---

<!--more-->

[We got our image created, what do we do next ?](http://cesarvr.github.io/post/deploy-ocp/) How do we automatically trigger deployments ? How do we orchestrate a security scan after an image is build ? [Image streams](https://docsropenshift.com/enterprise/3.0/architecture/core_concepts/builds_and_image_streams.html#image-streams) is the OpenShift answer to these questions. This object observes an image in the container registry and notify other objects (BuildConfig, DeploymentConfig, etc.). 


To illustrate how it works we can create a simple [image builder](http://cesarvr.github.io/post/deploy-ocp/) that publish images to the container registry and use an image stream to observe this container for latest changes. This command ```oc new-build``` will create these two objects.  

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

If your are not familiar with this command (```oc new-build```), it just transform the source code from a git repo into an image. Inside this image the Node.js application is ready to be executed. 

Here we got the following dependency: 

```
  Builder              Container Registry            Image Stream    
+----------+   push   +-------------------+  listen  +----------+
 node-build    -->    ...svc:5000/hello01     <--     node-build
+----------+          +-------------------+          +----------+ 
```


# Deploy 

Now that we have the image creation and ready for distribution let's work in the deployment. To deploy an image is very easy first we need the registry address of the image.

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

# Subscribing 

Sadly the DeployConfig is unaware of the existence of our image stream and it won't be notified when the image change. We need to subscribe our deployment controller, we do this using the ```oc set triggers``` command. 

```
   

```   




```sh
oc create dc hello-ms --image=docker-registry.default.svc:5000/hello01/node-build
```

Once we execute this command the deployment controller will grab the image and create a pod. 

![deployment](https://github.com/cesarvr/hugo-blog/blob/master/static/static/oc-image-stream/oc-deploy-is.gif?raw=true)







