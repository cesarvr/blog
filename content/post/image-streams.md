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

In the last post we learn how to build software from source code to immutable images the next question you may ask is how you deploy this image. Deployment of software in OpenShift is handled by an entity called the deployment controller, aside from taking care of this task it also monitor the application state, making sure is always running. Let's deploy an image to see it in action.   

Let's deploy a simple Node.js application:

```
oc new-build nodejs~https://github.com/cesarvr/hello-world-nodejs --name node-build
```

This builder creates and publish a new image in the image stream with the same name (*node-build*). To deploy it, we have to create a deployment controller pointing to its location in the registry.

```
oc create dc node-server --image=docker-registry.default.svc:5000/hello01/node-build

# We check the status
oc get pod

NAME                  READY     STATUS      RESTARTS   AGE
node-server-1-pdjkc   1/1       Running     0          14m
```

Our pod is up and running and ready to handle traffic. But this method is not very scalable, What do I mean by that ? Every time we change our code we need to perform the same commands. In reality is only two commands we just need to trigger both objects BuildConfig and DeployConfig. Another option is to use some kind of watch, that every two seconds it call a script to update the state of our deployment with the latest changes from the git repository. That approach is not that bad, but there is a better way to do this.

The first step to automate this is to automate our BuildConfig, we are going to use a Webhook. Webhook is just a call/protocol that some git repository providers like Github, Bitbucket, etc. Used to notify third parties of any change in your repository/branch.

I'm going to use for this example the Github Webhook. First step is to get the token and URL:  

- Token

```
# getting the secret token
oc get bc node-build -o yaml | grep github: -A 2

 - github:
     secret: <some-alpha-numeric-token>
   type: GitHub
```

> Just small note, the token is base64 so it can include symbols that are misleading. To avoid confutions copy everything from between the space.

- URL, Here there is two types of Endpoints generic and GitHub, we are going to use Github.

```
oc describe bc node-build | grep Webhook -A 2
Webhook Generic:
       URL:            <URL-OpenShift-Endpoint>/webhooks/<secret>/generic
       AllowEnv:       false
Webhook GitHub:
       URL:            <URL-OpenShift-Endpoint>/webhooks/<secret>/github
```

This information is available in OpenShift Web Console, you need to navigate to the section Project/Builds/Builds, then in the configuration tab.

![build-webhook-ui]()


## GitHub Webhook Config

Also for this to work you should use the OpenShift.io or your Openshift instance should be accessible from the Webhook client.

![webhook-github]()

If you want to try this yourself just [fork this project](https://github.com/cesarvr/hello-world-nodejs). Now that we got the information we need let's configure the Webhook in Github. You need to go to your project -> Settings -> WebHooks and you need to put this configuration.

- Payload URL: You need to put here the URL of your BuildConfig Webhook ```oc describe bc node-build | grep Webhook -A 2```  ```<URL-OpenShift-Endpoint>/webhooks/<put-your-secret-here>/generic```
- Content-type: **Application/JSON**
- Secret: <some-alpha-numeric-token> You can get this by doing ```oc get bc node-build -o yaml | grep github: -A 2 ```, copy the base64 secret content.
- Which Event: You can configure here what type of events you want(push, delete branch, etc.) I'll choose **Just the push event**.
- Active: should be checked.

![webhook-delivery]()



Now our build is automatically triggered everytime we make a change,




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
