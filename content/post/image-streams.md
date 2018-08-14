---
title: "Automating deployments in Openshift."
date: 2018-07-31T10:05:23+01:00
lastmod: 2018-07-31T10:05:23+01:00
draft: false
keywords: []
description: Learn how to deploy and automate deployments using  Webhooks and ImageStreams in OpenShift.
tags: [openshift, imagestream]
categories: [openshift, build, imagestream, webhook]
author: ""
images:
  - https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true


# You can also close(false) or open(true) something for this content.
# P.S. comment can only be closed
comment: true
toc: true
autoCollapseToc: false
contentCopyright: false
reward: false
mathjax: false
---

<!--more-->

An image is just a convenient way to store information, deploying an image is to copy the content of this package (the image) inside a Linux container. OpenShift go a extra mile by creating the container inside one or more computers inside your cluster it, also make sure the number of containers specify by the user are up and running and it make this happens in an specific order. The part of OpenShift in charge of this task is called the DeploymentConfig.      

Let's explore DeploymentConfig works by deploying a simple Node.js application. Before we start, we need to build and store our software inside an image using ```oc new-build```:

```
oc new-build nodejs~https://github.com/cesarvr/hello-world-nodejs --name node-build

#Image stream
oc get is
NAME         DOCKER REPO                                          TAGS
node-build   docker-registry.default.svc:5000/hello01/node-build  latest
```

By now we got our image ```hello01/node-build```, where *hello01* is my project or name space and *node-build* is the image name. Next step is to create a DeploymentConfig to handle the container creation.  

```
oc create dc node-server --image=docker-registry.default.svc:5000/hello01/node-build

# We check the status
oc get pod

NAME                  READY     STATUS      RESTARTS   AGE
node-server-1-pdjkc   1/1       Running     0           1m
```

Our container is up and running inside a pod. A pod is like as set of one or many containers and they role is to make them look like a single entity. Now that we've our application running, let check our Deployment config state.

```
oc get dc

NAME          REVISION   DESIRED   CURRENT   TRIGGERED BY
node-server   1          1         1         config
```

One of the main responsabilities of the DeploymentConfig is to check that the *DESIRED* number of containers match the *CURRENT* numbers of containers running in your cluster. Another responsability is to rollout new version of images.  

```
# start a new build, pull our code, build, new image, etc...
oc start-build node-build --follow
# build "node-build-2" started
# ...


# ... after the new image is pushed to the registry.
oc rollout latest node-server  
```

This two commands are enough to update your application, you can automate this by encapsulating this two command inside a script, if you are working alone that would be enough but, it won't scale well for bigger teams as you may need to organice better your releases.  


# Automating

We need to automate this in a way that, as a developer I never need to leave my IDE, I just want to  push my feature into the branch and in few minutes I should see the new change being deployed. Let's start by solving first the part where we push into the git repository, for that we need the git provider to somehow notify Openshit on any new push.

## Webhooks

Webhook are just a notification protocol implemented by some popular git providers like GitHub, Bitbucket, VST, etc. It usually work by setting up an endpoint to receive the notification and an action (that may vary depending on providers) you want to trigger this notification. The endpoint can be any service capable of handling that request like a BuildConfig, Jenkins Pipeline, etc.   

The BuildConfig has Webhook endpoint's to trigger automatic builds and it comes in two flavors, one using a generic protocol other specific for Github's Webhook. In this post I'm going to use Github one because my sample project is hosted there but this instructions should work for other providers as well.  

### Before we start

Before integrating with make sure your OpenShift instance is accessible. To setup the Webhook we need to provide and endpoint, we get this by following this steps:  

- To get the endpoint URL.

```
oc describe bc node-build | grep Webhook -A 1
Webhook GitHub:
       URL:    https://<openshift-instance>/apis/build/v1/namespaces/hello01/buildconfigs/node-build/webhooks/<secret>/github
Webhook Generic:
       URL:            https://<openshift-instance>/apis/build/v1/namespaces/hello01/buildconfigs/node-build/webhooks/<secret>/generic
```

- Now we need to replace the *<secret>* part with this information.

```
# getting the secret token for GitHub
oc get bc node-build -o yaml | grep github: -A 2

 - github:
     secret: <some-alpha-numeric-token>
   type: GitHub

# If you want the token to setup a Generic webhook then...
oc get bc node-build -o yaml | grep generic: -A 2
....
```

This information is also available in OpenShift Web Console, you need to navigate to the section Project/Builds/Builds, then in the configuration tab.

![build-webhook-ui]()


### Setting up our project


![webhook-github]()

If you want to practice just [fork this project](https://github.com/cesarvr/hello-world-nodejs), once you got it and you have the endpoint URL, we need to configure our Github project by navigating to Settings -> WebHooks:

- Payload URL: You need to put here the URL of your BuildConfig Webhook ```oc describe bc node-build | grep Webhook -A 2```  ```<URL-OpenShift-Endpoint>/webhooks/<put-your-secret-here>/generic```
- Content-type: **Application/JSON**
- Secret: <some-alpha-numeric-token> as mentioned above, you get this by running ```oc get bc node-build -o yaml | grep github: -A 2 ```.
- Which Event: You can configure here what type of events you want(push, delete branch, etc.) I'll choose **Just the push event**.
- Active: should be checked.

![webhook-delivery]()


Now our build is automatically triggered every time we make a change.



------------


## Deployment

When you run ``` oc new-build``` two objects with the same name are created, the BuildConfig as we discuss earlier build/package your application inside an image and Image Streams which handles the image address in the registry and more important they notify other objects (like DeploymentConfig's) when a new image is pushed.

First we need to look for the Image Stream we are interested by looking up with ```oc get is```:

```sh
oc get is

NAME             DOCKER REPO
node-build       docker-registry.default.svc:5000/hello01/node-build
```

Once we found it, we have to subscribe our DeploymentConfig using ```oc set trigger```:

```
oc set triggers dc/node-ms --from-image=hello01/node-build:latest -c default-container
```  

First parameter is the DeploymentConfig name, second parameter is the image stream and the third is the name of the container **default-container** is the name by default. Let's take a look at the final result.


![automatic deployment](https://github.com/cesarvr/hugo-blog/blob/master/static/static/ocp-deploy/ocp-automatic-deploy.gif?raw=true)





Once get here you can just forget about OpenShift existence and just work on your features, but of course as development progress you should take smaller steps toward introducing testing of this deployments.

Here are some ideas to explore with image streams, automatic triggering of Jenkins pipeline to check the image quality/security/digital signature or automating more [sophisticated builds](http://cesarvr.github.io/post/ocp-chainbuild/).
