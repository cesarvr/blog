---
title: "4 Ways to Build Applications in Openshift"
date: 2018-07-28T19:24:19+01:00
lastmod: 2018-07-28T19:24:19+01:00
draft: false
keywords: []
description: "If you are migrating legacy applications or creating an automatic build system, Openshift BuildConfig offers you various choices to help you with those challenges."
images:
  - https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
tags: [openshift, buildconfig]
categories: []
author: ""

# You can also close(false) or open(true) something for this content.
# P.S. comment can only be closed
comment: true
toc: true
autoCollapseToc: true
# You can also define another contentCopyright. e.g. contentCopyright: "This is another copyright."
contentCopyright: false
reward: false
mathjax: false
---

<!--more-->

In this post we are going to talk about 4 BuildConfig strategies to build your software. By that I mean transform your software project from source code into an ready to deploy image.

These strategies might be useful for people who look for:

  * Want to deploy new software.
  * Working with build automation system in Openshift.
  * Want to run existing software in Openshift.    
  * Your software runtime/library is not longer supported. 

To follow this guide you just need a [Openshift installation](https://github.com/cesarvr/Openshift) or you can access [Openshift.io](https://manage.openshift.com/) (I run my examples there so it should be fine) for free. Also you have other alternatives like [oc-client](https://github.com/openshift/origin/blob/master/docs/cluster_up_down.md) or if you prefer a Virtual Machine you can use [Minishift](https://github.com/minishift/minishift).


## Build configuration

The *BuildConfig* is an abstraction to handle your application construction process, this component is divided in two parts a builder image and source strategy:

- **Builder Image** A builder image is a *special* type of image/container provided by Openshift which include the build tools (gradle, maven, npm, pip, etc.), [scripts](https://github.com/openshift/source-to-image) to automatise build process and execution tools (node, python, jvm, etc.).   
  - Each programming language or framework require a specific builder image, if we use Node.js for example we should use the *nodejs* builder image, this builder image include everything necessary to build a Node.js application.     
  - To check the available builder images in your Openshift installation you can run:

```sh
# delete this < | awk '{ print $1 }' > for more information.
oc get is -n openshift | awk '{ print $1 }'

NAME
…
mysql
nodejs
wildfly
…
```

- **Source Strategy**  Here we define the content of our builder image, there are three types of sources available:
  - **Source code** We provide a git repository to the BuildConfig.
  - **Binary**  jar/war file, scripts or executable (the builder image provide the execution context).
  - **Dockerfile** We defined and build the image ourselves.    

Creating and administrating your BuildConfig's is a simple task:

```sh
# create
oc new-build --name <name> <options>

# search
oc get bc/<name>
```

Once we configure our object we need to start the building process by running:

```sh
oc start-build bc/<name>
```    


## 1 Source Code  

This source strategy is the most common one, because is basically the one used by default when you create an application using the catalog. The objective of this approach is, in simple terms, to pull your code from some git repository and give you back an immutable image.

```
oc new-build nodejs~https://github.com/cesarvr/hello-world-nodejs --name node-build
```

First parameter is the builder image, we are using *nodejs* then separated by ```~``` we pass the [git repository](https://github.com/cesarvr/hello-world-nodejs) and finally we choose a name for our build configuration *node-build*.


```
# The builder configuration.
oc get bc

# output
NAME         TYPE      FROM         LATEST
node-build   Source    Git          1
```

As we mention above, to compile/prepare we need to trigger the build:

```sh
oc start-build node-build --follow
  build "node-build-1" started …
```
### How it works

The BuildConfig instantiate a builder image (```nodejs``` in this case) and set the git URL as an environment variable, then the scripts inside this image take control and pull the code and execute ```npm install``` and push an image (code+dependencies) into Openshift private registry.    

You can find the destination of the produced image by typing:

```
oc get is node-build   

NAME          DOCKER REPO                                            TAGS      UPDATED
node-build    docker-registry.default.svc:5000/hello01/node-build    latest    11 minutes ago
```

Where ```docker-registry.default.svc:5000/``` is the server, ```hello01``` is the namespace/project and ```node-build``` is your image.


> *When to use this?* If your your project build setup is compatible with any of the builder images of the catalog or the cost of adapting your project to any of this images seems reasonable, then you should definitely use this option.

Before using the source code strategy, one thing to take into consideration is if your project is compatible with the builder image. Example: To run the Node.js application the [package.json](https://github.com/cesarvr/hello-world-nodejs/blob/master/package.json#L7) need to implement the [npm-start](https://docs.npmjs.com/cli/start) script. Same thing happens in J2EE, your project may require to use Maven and follow a specific [configuration](https://github.com/openshift/openshift-jee-sample/blob/master/pom.xml).

## 2 Binary

This strategy delegates the build process to you, but still provide you with the option of using the images of the catalog for execution:

First let create the build configuration:

```
 oc new-build nodejs --name node-binary --binary=true
```

Very similar to the one we use for source code but notice however the lack of git repository and the addition of ```binary=true```, this tell our image that we are just interested in the tools for running our application.

```
# The builder configuration.
oc get bc

# output
NAME         TYPE      FROM         LATEST
node-binary   Source    Binary       0
```

Now as we said before we need to handle the construction of our application externally:

```
git clone https://github.com/cesarvr/hello-world-nodejs
cd cesarvr/hello-world-nodejs
npm install  # install the depedencies.
```

After executing ```npm install``` our application is ready to run. Next step then is to push the content of our folder to the BuildConfig:    

```
oc start-build node-binary --from-dir=.
Uploading directory "." as binary input for the build ...
```
This command will push your scripts into the build configuration object and trigger the build process jumping all the building steps and just creating our image.

If you are a Java developer, you need to choose the appropriate builder image (wildfly, jboss or redhat-openjdk18), use ```--from-file``` instead of ```--from-dir``` and pass your *jar/pom.xml*.

 ```
 # Pushing jar binary
 oc start-build java-binary-build --from-file=root.jar

 # or Pushing pom.xml
 oc start-build java-binary-build --from-file=pom.xml
 ```

 Everything should work the same as our example above, only difference is that might take more time to boot up.

> *When to use this?* If you have a legacy build system/framework in place that is not compatible with any builder image, example: Wildfly only supports Maven and my team is using Gradle. What I would do in that case is to generate my binary as usual and then use this strategy to create my final image.  

## 3 Dockerfile

This way you take care of the build process and image creation but we want to delegate it's construction to the BuildConfig, this way it can grab the base image from our private/corporate repository. This method require us to define a Dockerfile and delegate it's construction to the BuildConfig.

Let's define our Dockerfile, I'll call it [build.Dockerfile](https://gist.github.com/cesarvr/fac37fa7825f5ad7a576801fed07d0c8).

```Dockerfile
FROM mhart/alpine-node:base-8
COPY * /run/
EXPOSE 8080
CMD ["node", "/run/app.js"]
```

Next we need to call to our ```oc new-build``` command like this:

```sh
 cat build.Dockerfile | oc new-build --name node-container --dockerfile='-'
```

The first section we pipe the content of the file to our ```oc new-build``` command, the ```--dockerfile='-'``` tells the command to read from [standard input](https://en.wikipedia.org/wiki/Standard_streams#Standard_input_(stdin)). This command requires that the files we want to work with (```COPY``` in this case) to exist in the folder where we made the call to ```oc new-build``` command, otherwise it won't work.


> Sadly Docker strategy is disable in Openshift.io, but good news is you can still practice by using [oc cluster up](https://github.com/openshift/origin/blob/master/docs/cluster_up_down.md) or [minishift](https://github.com/minishift/minishift).

To trigger the build:

```sh
oc start-build node-container
```

When you run this the container will be build according to our specifications in the *.Dockerfile*.  

> *When to use this?*  You should use this method when working with a runtime not supported by any builder image available (e.g., EJB 1.0, JDK 1.4, etc.).

## 4 Importing Images

This one not using a BuildConfig but I just included because is another option and can be useful in desperate circumstances. If you are creating your own images and pushing it to an external/internal registry then you can deploy this images in Openshift. You can do this by creating an image stream object.    

Importing an image inside your cluster is easy:

```
oc import-image microservice:latest --from=your-docker-registry.io/project-name/cutting-edge:latest --confirm
```   

This command creates the image stream pointing to your image. To check the object state you just need to write this command:  
```
oc get is

 Name                   Docker Repo                                  TAG           …
 microservice   your-docker-registry.io/hello01/cutting-edge:latest   latest    12 seconds ago
```

> *When to use this?*  If you have legacy applications running in containers and they are stored in an external registry like Nexus, then you can use this method to deploy your applications. Use this way only as temporary solution or as your last choice.   


# Optimizing 

Now that you know multiple ways to construct your application in the cloud using Openshift, you might want to know how to optimize those build to get the most efficient runtime container as possible. To help you with that I wrote this article on how to do [chain builds](http://cesarvr.github.io/post/ocp-chainbuild/), by chaining your builds you can divide the build process into two images one handling the build(compilers, build frameworks, etc) and the other image very small and with just the necessary for runtime.  


# Deploy

In the next post I'm going to talk about how can create a DeploymentConfig to deploy this images streams we have created so far ([node-build](#1-source-code), [node-binary](#2-binary), [node-container](#3-dockerfile) and [import](#4-importing-images)).

Many thanks to [Prima](https://github.com/primashah) for editorial help.
