---
title: "4 Ways to Build Applications in OpenShift"
date: 2018-07-28T19:24:19+01:00
lastmod: 2018-07-28T19:24:19+01:00
draft: false
keywords: []
description: "If you are migrating legacy applications or creating an automatic build system, OpenShift BuildConfig offers you various choices to help you with those challenges."
images:
  - https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
categories: [OpenShift, BuildConfig]
categories:
  - OpenShift
  - BuildConfig
  - ImageStream

# You can also close(false) or open(true) something for this content.
# P.S. comment can only be closed
comment: true
toc: true
autoCollapseToc: true
# You can also define another contentCopyright. e.g. contentCopyright: "This is another copyright."
contentCopyright: false
---
We are going to discuss the different strategies for building our software in OpenShift. These strategies are useful if you need to solve any of the following problems:
<!--more-->

* Learn how to build your software
* You want to automate your builds
* Build existing applications
* You want to run legacy applications inside containers on the cloud

You can run these examples in a local instance of OpenShift or a Virtual Machine. Also, if you don't want to install it locally, you can get free access to OpenShift.io.


## Build Configuration

Creating your own images requires some non-trivial knowledge about Linux systems setup. For this reason, OpenShift includes a set of images known as image builders. These images implement an opinionated way to build software that we can leverage to focus less in the configuration and more on the application development.

To check the images available to build our software, check out the following code:

```sh
# delete this < | awk '{ print $1 }' > for more information.
oc get is -n openshift | awk '{ print $1 }'

NAME
…
java
mysql
nodejs
wildfly
…
```

By the images name, we can infer what type of programming language or framework they support, so let's pick one of these images and build something.


## Building Your Applications From Source Code

This is the best way to get started with OpenShift, because it requires very little setup, and as long as you follow the guidelines of the builder image, your work is reduced to just passing a git repository URL.

Here is an example of building a Node.js application:

```
oc new-build nodejs~https://github.com/cesarvr/hello-world-nodejs --name node-build
```

This particular build (Node.js builder) has two stages: cloning your code from the git repository and resolve the dependencies using [npm](https://www.npmjs.com/) (this is a Node.JS package manager similar to Maven). When the project is ready to run, a snapshot is taken and is stored in the registry.

If we are able to restore this image to its previous state (project ready to run), then we can deploy this application with a high degree of confidence. That's the magic behind containers.

We can find the stored image by running the following command:

```
# The builder configuration.
oc get bc

# output
NAME         TYPE      FROM         LATEST
node-build   Source    Git          1

oc get is node-build   

NAME          DOCKER REPO                                            TAGS      UPDATED
node-build    docker-registry.default.svc:5000/hello01/node-build    latest    11 minutes ago
```


- **Pros:** Less complexity, easy for starters, and good for a greenfield project.
- **Cons:** Your code needs to be compatible with the build framework implemented by the image builder.

## Build an Application From Existing Binary

Sometimes, we won't be able to use the source to image approach, because we are previously generating the binary using a build automation service, or we are using a non-supported build framework. In this situation, we can still use the builder images for runtime.

In these cases, we can configure the build to receive a binary instead of source code. Let’s take this Spring Boot application. For example, I’ve created it using this getting started guide, and we are going to use Gradle, which is not supported, to demonstrate how to configure this type of build.

First, we need to clone this repository:

```
 git clone https://github.com/cesarvr/Spring-Boot spring-boot

 # enter to the directory
 cd spring-boot
```

Next generate an executable  .jar:

```
#Generate the binary executable file in ./builds/libs/
gradle bootJar

#We got a file named: hello-boot-0.1.0.jar
```

Now that we got the jar file, we need to choose the proper image builder to handle this binary. We are going to choose the java image. This image expects an executable jar file to run.

```
#Generate the build configuration
oc new-build java --name=java-binary-build --binary=true
```

The last step is to trigger the build:

```
oc start-build bc/java-binary-build \
--from-file=./build/libs/hello-boot-0.1.0.jar \
--follow
```

- **Pros:** Offers a convenient way to integrate with automation servers and unsupported build technology.
- **Cons:** The binary needs to be compatible with the runtime.  

## Creating Your Own Container

If you want to migrate applications, which runtime is not supported by any image builder (JDK1.4, COBOL, etc.), then you have to provide a runtime for this application to run, as long as the runtimes don't have any deprecated system calls. In which case, they will be easier to patch than trying to rewrite the whole stuff.

To provide this alternative runtime, you need to define your own container as part of the build configuration. To illustrate this point, we are going to create a minimal image to run our Node.js application above.

First, let's clone our application.

```
# clone the app
git clone https://github.com/cesarvr/hello-world-nodejs hellojs

cd hellojs
```

Once we are there, we create a [build.Dockerfile](https://gist.github.com/cesarvr/fac37fa7825f5ad7a576801fed07d0c8).

```Dockerfile
FROM mhart/alpine-node:base-8
COPY * /run/
```

First, we defined a base image to start our image from inside alpine-node and its a folder called run. We are going to copy the content of our project there.

```dockerfile
EXPOSE 8080
CMD ["node", "/run/app.js"]
```

Then, we set up the container to expose the port 8080 (that's the port we are using to accept traffic). Finally, we run the node against our script.

To create the build configuration:

```sh
cat build.Dockerfile | oc new-build --name node-container --dockerfile='-'
```

We create the build by using the new-build command,  but this time, we aren't going to define a builder image to use, instead, we are going to use the --dockerfile  parameter. The --dockerfile accepts a string containing Dockerfile instructions. If we pass a dash  --dockerfile='- ‘ , we can stream the contents of our [build.Dockerfile](https://gist.github.com/cesarvr/fac37fa7825f5ad7a576801fed07d0c8).

Also, the Dockerfile instructions are executed from the folder that we are making the call. This means that making the call from another folder can have undesired effects.

To trigger this build:

```sh
oc start-build bc/node-container --follow
```

**Pros:** Very flexible because you can define your own runtime.
**Cons:** Complex and difficult to maintain.

>Docker strategy is disabled in Openshift.io, but you can still practice using  [oc cluster](https://github.com/openshift/origin/blob/master/docs/cluster_up_down.md) up or  [minishift](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=1&cad=rja&uact=8&ved=2ahUKEwi--fnemIndAhWjKsAKHa2sCTcQFjAAegQIARAB&url=https%3A%2F%2Fgithub.com%2Fminishift%2Fminishift&usg=AOvVaw1Ii7xrRp4eDcimcndamKkI).


## Using External Images

This one does not use a BuildConfig, but I just included it because it is another option and can be useful in desperate circumstances. If you are creating your own images and pushing it to an external registry, you can still deploy this image in Openshift.

Importing an image inside your cluster is easy:

```
oc import-image microservice:latest \
  --from=your-docker-registry.io/project-name/cutting-edge:latest \
  --confirm
```   

To check your image, you just need to write this command:

```
oc get is

Name                   Docker Repo                                 
microservice   your-docker-registry.io/hello01/cutting-edge:latest
```

> *When to use this?* You can use this when you have legacy applications running in containers and they are stored in an external registry, like Nexus.    


# Deploying Your Application

We have our images; what do we do next? Deploying an image is easy; let see how to do this. First, we need to choose the image we want to deploy.

```sh
oc get is

NAME                DOCKER REPO                                                               
java-binary-build   docker-registry.default.svc:5000/hello01/java-binary-build   
node-build          docker-registry.default.svc:5000/hello01/node-build  
```

This command locates the images we have created so far (these are images sources are created automatically with every build configuration definition). The next step is to create an OpenShift application by choosing any of the images. I would use the  java-binary-build.

To create these components:

```sh
oc new-app java-binary-build --name=java-ms
```

Once this command finishes, our application should be deployed and running, but it won't be able to receive traffic. For that, we need to expose our application:

```sh
# Expose the service of our application
oc expose svc java-ms

# Now we want to know the URL.
oc get route

NAME        HOST/PORT                                                   
java-ms     java-ms-hello01.7e14.starter-us-west-2.openshiftapps.com

# URL for the exterior ^^
```

Our application should be available to [receive traffic](http://java-microservice-hello01.7e14.starter-us-west-2.openshiftapps.com/).

```sh
curl java-microservice-hello01.7e14.starter-us-west-2.openshiftapps.com
#Greetings from Spring Boot!
```


# Optimizing

Now that you know multiple ways to construct your application in the cloud using OpenShift, you might want to know how to optimize those build to get the most efficient runtime container as possible. To help you with that I wrote this article on how to do [chain builds](http://cesarvr.github.io/post/ocp-chainbuild/), by chaining your builds you can divide the build process into two images one handling the build(compilers, build frameworks, etc) and the other image very small and with just the necessary for runtime.  

Many thanks to [Prima](https://github.com/primashah) for editorial help.
