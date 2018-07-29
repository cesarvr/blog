---
title: "5 ways to build software in Openshift"
date: 2018-07-28T19:24:19+01:00
lastmod: 2018-07-28T19:24:19+01:00
draft: false
keywords: []
description: "In this article we are going to review the multiple ways to build an applications in Openshift. All this examples where done using [Openshift.io](https://manage.openshift.com/) which is a playground to practice."
images:
  - https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true 
tags: []
categories: []
author: ""

# You can also close(false) or open(true) something for this content.
# P.S. comment can only be closed
comment: true
toc: true
autoCollapseToc: false
# You can also define another contentCopyright. e.g. contentCopyright: "This is another copyright."
contentCopyright: false
reward: false
mathjax: false
---

<!--more-->

In this article we are going to review the multiple ways to build an applications in Openshift. All this examples where done using [Openshift.io](https://manage.openshift.com/) which is a playground to practice.


# Beginners

To deploy applications using this methods you basically don't need to much about Openshift objects --service, pod, router, etc. If you want to get started this is the best way.

## Console

The easiest way to deploy your application is to go to the dashboard and just choose a template from the catalog:

![deploying nodejs applications](https://github.com/cesarvr/Openshift/raw/master/assets/new-app-nodejs.gif?raw=true)



## Using new-app  

The method we use above has a command like equivalent called ```new-app```. In this example we are going to create an Node.js application using the nodejs image from the catalog and this [git repository](https://github.com/cesarvr/hello-world-nodejs).

```sh
 oc new-app --name node-app nodejs~https://github.com/cesarvr/hello-world-nodejs
```

This command will create the same components as the openshift console with the omission of the router object, this need be created manually by calling ```oc expose```.    

```
oc expose svc <name-of-the-service>
```

![new-app](https://github.com/cesarvr/hugo-blog/blob/master/static/static/ocp-deploy/oc-deploy.gif?raw=true)


Every time you write this two command Openshift will generate all the necessary objects to deploy your container and start directing to them, but there is a small inconvenience if you want to remove all the created objects let said you made a mistake you need to delete those one by one. But we are lucky that all the created objects share the same label, here is the command to clean those objects.    

```sh
 oc delete all -l app=node-app # this delete all the objects with label node-app
```

This command is a bit long and difficult to remember. What I do is to create a shell function inside my ```.bashrc``` or ```.zshrc``` like this one:    

```sh
 function rm-app {
   oc delete all -l app=$1
 }

 # The I called we can do this:
 source ~/.bashrc # or ~/.zshrc if your are using zsh
 rm-app node-app

 # deploymentconfig "node-app" deleted
 # buildconfig "node-app" deleted
 # imagestream "node-app" deleted
 # route "node-app" deleted
 # service "node-app" deleted
 #
```

> *When to use this?* This the best way to start. Then I would recommend to get little by little more ambitious with learning how this objects works because it will payoff big time when you start to get interested in more sophisticated configurations.

# Intermediate - Advance

Before reading this section make sure you dominate some of the basic concepts, if you want you can go through this [introduction](https://github.com/cesarvr/Openshift) guide. Which will help you understand the basic component of a typical application in Kubernetes/Openshift.

## Build configuration

 The first way we are going to try is to create a builder configuration object, this object is divide in two parts a builder image using [source to image](https://github.com/openshift/source-to-image) and source strategy which can be an git URL, binary or Docker configuration file.

 To create the build configuration is easy we just need to write this command:

 ```sh
oc new-build
 ```

## Git Repository

Let's create a build that use a git URL as source strategy, the command is very similar to ```new-app```.

```
oc new-build nodejs~https://github.com/cesarvr/hello-world-nodejs --name node-build
```

This command will create a build and [image streams](https://docs.openshift.com/enterprise/3.0/architecture/core_concepts/builds_and_image_streams.html#image-streams) object. It works in this way, first the build object creates the image using [source to image](https://github.com/openshift/source-to-image) and then it push this image to the [image streams](https://docs.openshift.com/enterprise/3.0/architecture/core_concepts/builds_and_image_streams.html#image-streams) object that basically is like a high level abstraction of a container image registry. Is easier to think about the registry as a image database where you can push and pull images from there.  

```
# The builder configuration.
oc get bc

# output
NAME         TYPE      FROM         LATEST
node-build   Source    Git          1


# The created image stream.
oc get is

# output
NAME         DOCKER REPO                                           TAGS      UPDATED
node-build   docker-registry.default.svc:5000/hello01/node-build   latest    9 minutes ago
```

To run this build you we just need to execute this command:

```
oc start-build node-build --follow
```

As soon as our build finish it store our image with our code ready to deploy into the registry and our image stream is tracking its URL ```docker-registry.default.svc:5000/hello01/node-build```.


> *When to use this?* If you to take your code directly from the git repo and transform it into a immutable image ready to deploy this is the way to go.

## Binary

This type of build configuration works without git repository at all, it just wait for us to provide the binary or if we are using an interpreted language we should provide the script.

First let create the build configuration:

```
 oc new-build nodejs --name node-binary --binary=true
```

Very similar to the one above but notice the lack of git repository and the addition of ```binary=true```, this tell our image to wait until we provide the source. Also, as we see before, this command creates an image stream and build config.

```
# The builder configuration.
oc get bc

# output
NAME         TYPE      FROM         LATEST
node-binary   Source    Binary       0

# The created image stream.
oc get is

# output
NAME         DOCKER REPO                                           TAGS      UPDATED
node-binary   docker-registry.default.svc:5000/hello01/node-binary
```

As we mention before this method require that we provide the binary, so let first clone that repository manually:

```
git clone https://github.com/cesarvr/hello-world-nodejs
cd cesarvr/hello-world-nodejs
```

Now we are inside our folder where our scripts are we need to push the content to the build.

```
oc start-build node-binary --from-dir=.
Uploading directory "." as binary input for the build ...
```
This command will push your scripts into the build config process and it will trigger, think of it like a replacement of the ```git clone``` command in the usual build process.

 If Java is your thing the steps are almost the same but you would be interested in the ```.jar``` file. You should use ``` --from-file= ``` instead and of course, the build image should be Java compatible:

 ```
 # Pushing jar binary
 oc start-build java-binary-build --from-file=root.jar

 # Pushing pom.xml
 oc start-build java-binary-build --from-file=pom.xml
 ```

 Everything should work the same as our example above, only different is that may take more time.

> *When to use this?* This type of builds are great when you are using our going to use an alternative mechanism to build the binary. Typical situation are working in a established or legacy Jenkins configuration outside of Openshift that generates the binary. Then this type of build config is for you.


## Dockerfile

This way of creating a build config expects a Dockerfile to build our image, which mean there is not involvement of [source to image](https://github.com/openshift/source-to-image).

Let's define our Dockerfile, I'll call it [build.Dockerfile](https://gist.github.com/cesarvr/fac37fa7825f5ad7a576801fed07d0c8).

```Dockerfile
FROM mhart/alpine-node:base-8
COPY * /run/
EXPOSE 8080
CMD ["node", "/run/app.js"]
```

Next we need to call to our ```oc new-build``` command like this:

```sh
 cat build.Dockerfile | oc new-build --name node-docker --dockerfile='-'
```

To trigger the build:

```sh
oc start-build node-docker
```

> *When to use this?*  We should use this type when we are working with a legacy pipeline that create containers as the delivery medium for the application. You can use this in the mean time while you plan a proper migration to source to image as a way to create images.



# Deploy

Now that we got our 3 alternatives git based, binary and docker file then next step is to deploy our code so they can start receiving traffic. I'll choose the ```node-binary``` build but this steps can be reuse for the other two build config.

```sh
oc get is

NAME          DOCKER REPO                                            TAGS      UPDATED
node-binary   docker-registry.default.svc:5000/hello01/node-binary   latest    27 minutes ago
```

Having the address of our image, now we just simply call:

```sh
oc create dc hello-ms --image=172.30.1.1:5000/hello/runtime
```

Now that we create our deployment object, we now need to send some traffic to our application. Before start sending traffic we need to identify by looking up is label.

```sh
oc get dc hello-ms -o json | grep labels -A 3
# returns
"labels": {
            "deployment-config.name": "hello-ms"
          }
```

Now let create a service and send some traffic directed to this label:


```sh
oc create service loadbalancer  hello-ms --tcp=80:8080
# service "hello-ms" created

# edit the service object
  oc edit svc hello-ms -o yaml
```

This will open the service object in yaml format in edit mode, we need to locate the *selector* and replace with the label of our deployment object.

From this:

```yml
selector:
  app: hello-ms
```

To this:

```yml
selector:
 deployment-config.name: hello-ms
```

We can do this the other way around, at the end is just a matter of taste. Next we need to expose our service:

```
oc expose svc hello-ms
# route "hello-ms" exposed

oc get route
NAME       HOST/PORT                                                   PATH      SERVICES     PORT          
hello-ms   hello-ms-hello01.7e14.starter-us-west-2.openshiftapps.com              hello-ms   80-8080                
```

Now know the URL we can confidently make a ```curl``` to that address:  


```
curl hello-ms-hello.127.0.0.1.nip.io
Hello World%
```

If my pod are not in sleeping (remember is a demo instance). You can access them using this [URL](hello-ms-hello01.7e14.starter-us-west-2.openshiftapps.com).


# Wrapping Up

Hope you have learn the multiple ways to build an application in Openshift. If you feel brave after this and want to learn more sophisticated ways to build software I'll recommend to read about [chaining builds](http://cesarvr.github.io/post/ocp-chainbuild/).  
