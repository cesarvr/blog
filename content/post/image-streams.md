---
title: "Automate your application deployments in OpenShift."
date: 2018-07-31T10:05:23+01:00
lastmod: 2018-07-31T10:05:23+01:00
draft: false
keywords: []
description: "How to automate your deployments with Webhooks and ImageStreams in OpenShift."
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

An image is just a convenient way to store information, when you deploy an image it basically means to copy the content of this package (the image) inside a Linux container. OpenShift go a extra mile by creating the container in a remote location (a computer inside the cluster), making sure the number of containers specify by the user are up and running and making this happens in the right order. The part of OpenShift in charge of this task and is called the DeploymentConfig.      

Let's explore how this works by deploying a simple Node.js application. Before we deploy we need to build and seal our software inside an image using ```oc new-build```:

```
oc new-build nodejs~https://github.com/cesarvr/hello-world-nodejs --name node-build

#Image stream
oc get is
NAME         DOCKER REPO                                          TAGS
node-build   docker-registry.default.svc:5000/hello01/node-build  latest
```

Our software has been prepared (or compiled if your are using other programming languages) and stored in the image ```hello01/node-build```, where *hello01* is my project or name space and *node-build* is the image name. Now that we have an image, we just need to create a DeploymentConfig to handle how this image will transition to a container inside our cluster.  

```
oc create dc node-server --image=docker-registry.default.svc:5000/hello01/node-build

# We check the status
oc get pod

NAME                  READY     STATUS      RESTARTS   AGE
node-server-1-pdjkc   1/1       Running     0           1m
```

Our image has been deployed into a container inside a pod, think of pod like as set of one or many containers and they role is to enforce common rules between them and make them look like a single entity.

We can check the state of our DeploymentConfig by running:

```
oc get dc

NAME          REVISION   DESIRED   CURRENT   TRIGGERED BY
node-server   1          1         1         config
```

And we can update and deploy a new image by doing:

```
# start a new build, pull our code, build, new image, etc...
oc start-build node-build --follow
build "node-build-2" started


# ... after the new image is pushed to the registry.
oc rollout latest node-server  
```

Two commands only and we got our code running in a node (a computer inside a cluster), but we can automate this.

# Automating

By now we understand how the build and deployment stage are handled in OpenShift, but there is a problem, all this steps aren't automatic yet, if you trigger a new build our application will be updated but we still need to deploy the image ourselves by calling.  
We need to implement a way to observe the image state in the registry and trigger the deployment automatically when the image is updated, we can do this by running some shell script, that scan the registry every few seconds but that is not so elegant. For this type of problem OpenShift have something called image streams.

Every time we run ``` oc new-build ...```, an image stream is created to observe the image for updates and notify its subscribers. To deploy the new version of the image we just need to subscribe our deployment controller to this image stream.   

To get the image stream associated to our build we just need to execute ```oc get is```:

```sh
oc get is

NAME             DOCKER REPO
node-build       docker-registry.default.svc:5000/hello01/node-build
```

We see here that it share the same name with the BuildConfig, we just need to subscribe our deployment controller using ```oc set trigger```:

```
oc set triggers dc/node-ms --from-image=hello01/node-build:latest -c default-container
```  

First parameter is the DeploymentConfig, second paramter is the image stream and the third is the name of the container **default-container** is the name by default. Let's take a look at the final result.


![automatic deployment](https://github.com/cesarvr/hugo-blog/blob/master/static/static/ocp-deploy/ocp-automatic-deploy.gif?raw=true)



## Webhooks

That was a good step towards automation, we've reduce the amount of command to just one. We still need to do ```oc start-build``` to trigger the build.

In this section we are going to discuss how to eliminated that step and go to a flow where we push our code and we just need to wait until it gets deployed.

Webhook to those who don't know, is just a notification protocol implemented by some of the popular git providers like GitHub, Bitbucket, VST, etc. BuildConfig implement two types of webhook endpoints one using a generic protocol other specific for Github. In this post I'm going to use Github, as the sample project I'm using is hosted there but the instruction should work for other providers.  

### Before we start

Keep in mind before integrating with any Webhook is that we just need to make sure our OpenShift instance is accessible. To setup the Webhook we need to provide and endpoint, we get this by following this steps:  

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


Now our build is automatically triggered everytime we make a change.


Once you are here you can just forget about OpenShift existence and just work on your features, and the you can take smaller steps toward automating the testing of this deployments. Also you can think of way to use image streams to trigger Jenkins pipeline to check the image quality/security. Those are some of the ideas to fully take advantage of the image streams.     
