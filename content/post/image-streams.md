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

In the last post we learn how to build software from source code to immutable images, the next question you may ask is how you deploy this images. To deploy images Openshift use an entity called the deployment controller, which no only deploy applications using images from the registry, but also it make sure that those applications are always available.

Let's explore how it works by deploying a simple Node.js application:

```
oc new-build nodejs~https://github.com/cesarvr/hello-world-nodejs --name node-build
```

This command will build our code and creates an image then it push this image to the registry. Next step is to create the deployment controller to execute our application.   

```
oc create dc node-server --image=docker-registry.default.svc:5000/hello01/node-build

# We check the status
oc get pod

NAME                  READY     STATUS      RESTARTS   AGE
node-server-1-pdjkc   1/1       Running     0          14m
```

Now our application is ready to handle some traffic.


# Automating

By now we understand how the build and deployment stage are handled in OpenShift, but there is a small problem our current configuration is not automatic. if you update the image by running a new build:

```
oc start-build bc/node-build --follow
```

It won't get deployed automatically. We need to look for a way to listen for a particular image changes and everytime it changes notify the deployment controller.

That's basically the main duty of the image streams. Every time we run ``` oc new-build ...``` an image stream is created to observe the state of the image and notify subscribers. We just need to subscribe our deployment controller.   

To get the image stream associated to our build we just need to execute ```oc get is```:

```sh
oc get is

NAME             DOCKER REPO
node-build       docker-registry.default.svc:5000/hello01/node-build
```

As you might see it share the same name with the BuildConfig, we just need to subscribe our deployment controller using ```oc set trigger```:

```
oc set triggers dc/node-ms --from-image=hello01/node-build:latest -c default-container
```  

First parameter is the DeploymentConfig, second paramter is the image stream and the third is the name of the container, this because pods can run more that one container inside. Let's take a look at the final result.


![automatic deployment](https://github.com/cesarvr/hugo-blog/blob/master/static/static/ocp-deploy/ocp-automatic-deploy.gif?raw=true)



## Webhooks
I'm cannot call this thing automatic, if for every new push I need to get outside of my IDE and execute the build my self. The ideal scenario is to push new code and automatically deploy it. To achieve this we are going to setup a Webhook.

Webhook to those who don't know, is just a notification protocol implemented by some of the popular git repos providers like GitHub, Bitbucket, VST, etc. BuildConfig implement two types of webhook endpoints one generic the other more specific for Github. For this post we are going to use Github.  

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



Now our build is automatically triggered everytime we make a change.



We've so far use image stream to automatically deploy our images into a pod, but they are other use cases like triggering BuildConfig's (We can use the [contents of an image to create another image](https://cesarvr.github.io/post/ocp-chainbuild/)) or we can trigger a Jenkin's task that check the container for vulnerabilities, valid signature, etc.
