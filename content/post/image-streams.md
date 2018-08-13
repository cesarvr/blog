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

In the last post we learn how to build software starting from source code to producing immutable images, the next question is how you deploy this images. To deploy images OpenShift we need to create something called deployment controller, which no only deploy applications from images, but also make sure that those applications are always running.

Let's explore how this works by deploying a simple Node.js application. Before we deploy we need to build and package our application:

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

By now we understand how the build and deployment stage are handled in OpenShift, but there is a problem, all this steps aren't automatic yet, if you trigger a new build our application will be updated but we are still need to deploy the image ourselves.  
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
