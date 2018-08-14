---
title: "Automating deployments in Openshift."
date: 2018-07-31T10:05:23+01:00
description: Learn how to deploy and automate deployments using  Webhooks and ImageStreams in OpenShift.
tags: [openshift, imagestream]
categories: [openshift, build, imagestream, webhook]
author: ""
images:
  - https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
toc: true
---


When you deploy an application in Openshift, you are just copying the content of an image inside a Linux container. But OpenShift go an extra mile by creating the containers inside one or more computers in your cluster and making sure that the containers specified by the user are up and running. The piece in charge of this tasks is the DeploymentConfig.      

<!--more-->

Let's explore how DeploymentConfig works by deploying a simple Node.js application. First, we need to build our application and store the resulting executable inside an image:

```sh
oc new-build nodejs~https://github.com/cesarvr/hello-world-nodejs \
    --name node-build

#Lookup our image
oc get is

NAME         DOCKER REPO                                          TAGS
node-build   docker-registry.default.svc:5000/hello01/node-build  latest
```

We have created our image and is stored in this part of the registry ```docker-registry.default.svc:5000/hello01/node-build```, where *hello01* is my project or name space and *node-build* is the image name. Let's deploy this image by creating a DeploymentConfig.  

```sh
oc create dc node-server \
  --image=docker-registry.default.svc:5000/hello01/node-build

# We check the status
oc get pod

NAME                  READY     STATUS      RESTARTS   AGE
node-server-1-pdjkc   1/1       Running     0           1m
```

Our container is up and running inside a pod. A pod is like as set of one or many containers and they role is to make them behave as single entity. To test that everything is running correctly


## Making a new release

Let's make some changes into our program, we have at the moment something like this:  

```js
require('http').createServer((req, res) => {
 res.end( 'Hello World V1')
}).listen(8080)
```

Let's bump the version and see how we can update this application:

```js
require('http').createServer((req, res) => {
 res.end( 'Hello World V2')
}).listen(8080)
```

First we need to build the code again, but this time we don't need to create everything again, we just need to trigger a build.

```sh
# start a new build, pull our code, build, new image, etc...
oc start-build node-build --follow
# build "node-build-2" started
# ...

```

Once the image is create let's deploy it:

```sh
# ... after the new image is pushed to the registry.
oc rollout latest node-server  
```

Now let check that our application is updated. To check this I won't create a service or router for this, I want to show you another way to comunicate with your pods using ```oc exec```.

```sh
#first we need the pod name.
oc get pod
node-server-2-tdhg6   1/1       Running     0           1m

oc exec node-server-2-tdhg6 -- curl 0.0.0.0:8080  
# Hello World V2
```

A simple explanation is that ```oc exec``` allows you to run shell command in remote pod is like ```docker run``` in another computer. I just run ```curl -s``` against the local IP address in port 8080, which basically return the server payload. Use this command when you need to debug or do a quick check in your pods, also this is useful when you deal with Jenkins.


# Automating

With our knowledge so far, we can automate our release by merging those two command in one script, but I'll show you a more civilize way. I just want to push my code into the branch and in few minutes I just want see the new change being deployed, so let's take that flow as our goal.

Let's start by solving the part where we push into the git repository, for that we need the git provider to somehow notify OpenShift on any new push.

## Webhooks

Webhook are just a notification protocol implemented by some popular git providers like GitHub, Bitbucket, VST, etc. It usually work by setting up an URL address where we want to send the notification and an action (that may vary depending on providers) to trigger this notification. The receiver can be any web service capable of handling that request like a BuildConfig, Jenkins Pipeline, etc.   

BuildConfig's has two Webhook endpoints to trigger automatic builds, one is a generic Webhook hanlder the other endpoint is specific for Github's Webhook. I'm going to use Github for this because my sample project is hosted there but the instructions are the same for other providers as well.  

### Before we start

Before we start make sure your OpenShift instance is accessible from the internet, that means you cannot test this with ```oc-cli``` or minishift. One alternative is to use [Openshift.io](https://manage.openshift.com/) account.

- To setup the Webhook we need to provide the receivers URL. The receiver in this case will be our BuildConfig.

```sh
oc describe bc node-build | grep Webhook -A 1

Webhook GitHub:
       URL: https://<OCP-big-URL>/.../webhooks/<secret>/github
Webhook Generic:
       URL: https://<OCP-big-URL>/.../webhooks/<secret>/generic
```

- Now that we have our URL we need to replace the <*secret*> part with secrets tokens, both alternative can be found be doing:

```sh
# getting the secret token for GitHub
oc get bc node-build -o yaml | grep "github:\|generic:" -A 1

 - github:
     secret: <some-alpha-numeric-token> #-QWCCVVVV....
 - generic:
     secret: .....

```

This information is also available in the OpenShift Web Console, you need to navigate to the section Project/Builds/Builds, configuration tab.

![build-webhook-ui](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/static/oc-image-stream/oc-automation/build-webhook-ui.PNG)


### Setting up our project


![webhook-github](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/static/oc-image-stream/oc-automation/webhook-github.PNG)

If you have a Github account you can [fork this project](https://github.com/cesarvr/hello-world-nodejs). Once your have your project in Github, you need to configure the Webhook in Settings -> WebHooks, and add the following information:

- Payload URL: You need to put here the URL of your BuildConfig Webhook.
- Content-type: **Application/JSON**
- Secret: <some-alpha-numeric-token>
- Which Event: You can configure here what type of events you want(push, delete branch, etc.) I'll choose **Just the push event**.
- Active: should be checked.

Once you complete this information you can test to see if the integration is successful.

![webhook-delivery](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/static/oc-image-stream/oc-automation/webhook-deliver.PNG)


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

```sh
oc set triggers dc/node-ms --from-image=hello01/node-build:latest -c default-container
```  

First parameter is the DeploymentConfig name, second parameter is the image stream and the third is the name of the container **default-container** is the name by default. Let's take a look at the final result.


![automatic deployment](https://github.com/cesarvr/hugo-blog/blob/master/static/static/ocp-deploy/ocp-automatic-deploy.gif?raw=true)





Once get here you can just forget about OpenShift existence and just work on your features, but of course as development progress you should take smaller steps toward introducing testing of this deployments.

Here are some ideas to explore with image streams, automatic triggering of Jenkins pipeline to check the image quality/security/digital signature or automating more [sophisticated builds](http://cesarvr.github.io/post/ocp-chainbuild/).
