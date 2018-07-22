---
title: "Chaining Builds In Openshift"
date: 2018-07-21T11:18:43+02:00
showDate: false
toc: true
description: Creating efficient and small image (low surface for attacks) by using chained builds in Openshift.  
---


# Chain builds 

Chain builds is a nice feature of Openshift that allows to compose various builder configurations helping us to decouple actions between each of them. In this article we are going to take advantage of this feature to sepparate the creation from the runtime of our application.

## New application

Openshift provides a convenient way to transform your source code to an running application in the cloud, actually, it offers various ways to achieve this. Creating a Node.js application is as simple as to do this:

```sh
 oc login -u user
 oc new-project hello

 # Assuming you are logged and you have a project you can start here.
 oc new-app --name node-app nodejs~https://github.com/cesarvr/hello-world-nodejs #new app using nodejs:latest (Node.js 8)
```

This command will create the backbone (BuildConfig, DeploymentConfig and Service) to orchestrate the deployment of your source code to a running application. 

## The problem 

Let's review the our final image:  

```
# We log into our container and run 
cd /
du -sh
474M	.
``` 

We found our image weight to much **474M** relative to the amount of code we are running. 

```js
require('http').createServer((req, res) => {
    res.end('Hello World')
}).listen(8080)
```


The problem is that the tools we use to build our application (gcc, g++, npm, yum cache, etc.) is bundle together with the application itself.

## Slim is better

A bigger image has a cost in your cluster, some of the disadvatages are: 

- Higher cost in CPU & Ram to deploy into a pod.
- They add more stress on the network. 
- Your vulnerability scanner catch libraries your application don't need at runtime. 

# Chaining containers

The strategy to solve this problem is to have two images one with the tools to build the image and a second one with the essential libraries for runtime. Let's see how much we can improve those **474M**. 


## Builder image 

Let's create the image with the necessary tooling to build our application:

```sh
oc new-build nodejs~https://github.com/cesarvr/hello-world-nodejs \
--context-dir=. \
--name=builder   
```   

- ```nodejs``` New build using nodejs (Node.js 8) as our base image which include the tools we need to build our software. 

- The [repository for our code repository](https://github.com/cesarvr/hello-world-nodejs). 

- ```context-dir``` This parameters tells where is the code.


This command will create a two OpenShift objects: 


* **BuilderConfig** This object handle the image creation thanks to [s2i](https://github.com/openshift/source-to-image). 

```sh
#builder configuration
oc get bc   
NAME      TYPE       FROM      LATEST
builder   Source     Git         1
```

* **ImageStream** It's like the middleman between this particular image and everything else. After a successfull build the resulting image is streamed here. 

```sh
oc get is
NAME          DOCKER REPO                         TAGS      UPDATED
builder       172.30.1.1:5000/hello/builder       latest    6 hours ago
```

If everything is sucessfull at this stage our code is cloned and dependencies pulled from npm. Artifacts are store inside an image called *builder* folder  ```/opt/app-root/src/```. 



## Runtime image 

Now we need to create the image that will take care of the runtime. Let's start by explaining this version of the ``` oc new-build``` command:  

```sh
oc new-build  --source-image=builder \
--source-image-path=[source-dir]:[destination-dir] \
--dockerfile='-' --name=runtime
```
- ```source-image``` We want the [nodejs image we created above](#builder-image).
- ```--source-image-path``` We want to copy some files from [that image](#builder-image). 
- ```dockerfile``` We want to create a new image using those files. Note: writing ```'dockerfile='-'``` will allow us to feed the Dockerfile via [standard input](https://en.wikipedia.org/wiki/Standard_streams#Standard_input_(stdin)).

Now that we know how to do it, we should create a file called [runtime.Dockerfile](https://gist.github.com/cesarvr/fac37fa7825f5ad7a576801fed07d0c8) to store the definition of our runtime container. 

```Dockerfile
FROM mhart/alpine-node:base-8
COPY * /run/
EXPOSE 8080
CMD ["node", "/run/app.js"]
```

We execute the command: 

```sh
cat runtime.Dockerfile | oc new-build --name=runtime \
--source-image=builder \
--source-image-path=/opt/app-root/src:. \
--dockerfile='-'
```

We copy the contents of [builder](#builder-image)/opt/app-root/src/ into the a temporary folder, then our Dockerfile use this folder as it's context folder. When we apply ```COPY * /run/``` we basically are copying the content of this temporary folder into our new runtime container.









