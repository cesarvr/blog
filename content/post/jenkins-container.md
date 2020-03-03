---
title: "Decoupling Jenkins Builds In Openshift"
date: 2020-02-17T18:37:00Z
draft: false
---

I was given the task to help my co-workers understand and take advantage of the Openshift container platform (based on Kubernetes). So I decided to write some guides on how to automate, build and deploy applications in Openshift. One of those guides was a minimal getting started Jenkins guide that looks something like this:

```java
pipeline {

  agent {
    label 'nodejs'
  }

  stages {
    stage("Creating Openshift Components") {
      steps {
        sh "node -v"
      }

      /* More steps */

    }
  }
}
```

> This code will schedule and execute a Jenkins job to be run inside a container labeled ``nodejs`` (provided by Openshift).

The output:


```sh
[Pipeline] stage
[Pipeline] { (Creating Openshift Components)
[Pipeline] sh
[test] Running shell script
+ node -v
v8.16.1
[Pipeline] }
[Pipeline] // stage
[Pipeline] }
```

This was very welcome by the teams, but as soon as they started to implement this they started to face some challenges. A team in particular was trying to develop something in Angular 8 which required minimum Node 10 and as you can see for the logs the official supported version in that [NodeJS-Slave-Container](https://access.redhat.com/containers/#/registry.access.redhat.com/openshift3/jenkins-agent-nodejs-8-rhel7) is 8. 

Another challenge they where facing was adding configuration files to their build. I try to dodge that bullet by suggesting them to use the Jenkins master to perform this configuration updates, but then we discovered that the Jenkins master was ephemeral (no storage) so when they restart they lost all changes.
  

## Another Approach

So after all this good feedback I started to look for alternatives ways to improve this, so I wrote this wishlist of features for a good pipeline code:

* *It should be flexible.* 
  - It should be easy to reuse Openshift images in the Jenkins script. If this fails teams usually start making/customizing their own images adding maintenance overhead.

* *Easy to customize.* 
  - Adding a configuration file or storage to a build should be defined in the Jenkins DSL.

* *Composable.* 
  - Use the best container for the job.

* *Simple*. 
  - No Dockerfile and no black-magic (like installing NVM at runtime).

## Kubernetes Plugin For Jenkins

I was under the impression that the [Kubernetes Plugin](https://github.com/jenkinsci/kubernetes-plugin) just provide a nice UI to configure Kubernetes/Jenkins related stuff, but after reading the docs carefully I discover that with this plugin you can actually define your own *jenkins-agents-pods*, instead of just using Openshift's pre-defined solution.

### What Is A Pod

A [pod](https://kubernetes.io/docs/concepts/workloads/pods/pod/) is a Openshift/Kubernetes entity that can be thought as a *container with one or more containers inside*. The original idea behind this is that you can deploy multiple piece of software that are tightly coupled together (like and old multi-tier application). But we can also think of it as a way to decouple task (like objects in OOP) -- i.e., you can use an image to build your code and delegate the deployment to another image. 


### Creating A Pod 
 
To define our pod (*or container of containers*) we use this function:

```java
podTemplate(cloud:'openshift', label: BUILD_TAG,  containers[/*...*/], /*...*/ )
```
Where:

* ``cloud`` This should point to the Kubernetes configuration. I'm running this on ``openshift``, so its default choice.

* ``label`` is a way to identify the pod, this allows the plugin to locate your pod in the cluster.

* ``container`` is an array of container objects, you can define containers using ``containerTemplate`` function.


#### Running Containers Inside

To define a container we use:

```java
containerTemplate(name: ‘’, image: ‘’, /*...*/ )
```

Where:

- ``name`` The container name.
- ``image`` The image to instantiate the container (for example: ``rhel7:latest``).


> For more documentation for [the Kubernetes Plugin](https://github.com/jenkinsci/kubernetes-plugin).


## Hello World


First let's look for an image that support Angular 8:

```sh
oc get is -n openshift | grep node
#nodejs docker-registry.default.svc:5000/openshift/nodejs 10,4,6 + 4
```

> You can get your cluster admin to create/update the image stream for [Node:12](https://access.redhat.com/containers/#/registry.access.redhat.com/rhel8/nodejs-12) if you want to target the [LTS](https://nodejs.org/en/).

We can see that the ``nodejs:10`` is the supported image so let's work with that and write our Jenkins script:

```java
def NODEJS_IMAGE = 'docker-registry.default.svc:5000/openshift/nodejs:10'
def NODEJS_CONTAINER_NAME = 'nodejs'

podTemplate(cloud:'openshift', label: BUILD_TAG,

  containers: [
      containerTemplate(name: NODEJS_CONTAINER_NAME, image: NODEJS_IMAGE,
       ttyEnabled: true,
       command: 'cat'),
  ] ) {

    node(BUILD_TAG) {

        container(NODEJS_CONTAINER_NAME) {
            stage('Hello World') {
                echo "build: " + BUILD_TAG
                sh 'node -v'
            }
            /* More stages */
        }

    }
}
```

> You can practice this by creating a new pipeline type of [item in Jenkins](https://jenkins.io/doc/pipeline/tour/hello-world/).

> The ``command:cat`` and ``ttyEnabled`` is just a small hack to avoid a *race condition* between Jenkins and the container, this will block the container until Jenkins logs-in into the container and execute the job.   

The output:

```sh
[Pipeline] stage
[Pipeline] { (Hello World)
[Pipeline] echo
build: jenkins-ctest-test-5
[Pipeline] sh
[test] Running shell script
+ node -v
v10.13.0
[Pipeline] }
[Pipeline] // stage
[Pipeline] }
```

Nice, we not longer need to wait for Red Hat to update their NodeJS Jenkins slave and the team can use any official image to accomplish their builds. Let's see how do we deal with state.

## Customizable

Another thing we wanted was to be able to add configuration files (without touching Jenkins Master) to the build job, let's create add a configuration file via [Config Map](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/).

First let's create a [Config Map](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/):

```sh
echo "Hola Mundo" >> hello.txt
oc create configmap hello-es --from-file=hello.txt
```

Now let's add this *configuration file* to our build:

```java
def NODEJS_IMAGE = 'docker-registry.default.svc:5000/openshift/nodejs:10'
def NODEJS_CONTAINER_NAME = 'nodejs'

podTemplate(cloud:'openshift', label: BUILD_TAG,

  /*
    We can attach the volumes here:
      configMapVolume(configMapName:'', mountPath:'')
      persistentVolumeClaim(claimName:'', mountPath:'')
  */
  
  volumes: [configMapVolume(configMapName: "hello-es", mountPath: "/my-config")],

  /*
    
  */

  containers: [
      containerTemplate(name: NODEJS_CONTAINER_NAME, image: NODEJS_IMAGE,
       ttyEnabled: true,
       command: 'cat')
  ] ) {

    node(BUILD_TAG) {

        container(NODEJS_CONTAINER_NAME) {
            stage('Hello World') {
                echo "build: " + BUILD_TAG
                sh 'node -v'
            }

            stage('Translating To Spanish'){
              echo "Hello World: "
              sh "cat /my-config/hello.txt"
            }
        }

    }
}
```

> ``mountPath:`` refers in what folder inside the container you want to mount the Config Map, you need to specify a folder, if the folder is not there it will be created. 


## Composition

Now this is getting interesting, sometimes having the right version of the framework is not enough like in the example above, Node-10 doesn't have the tools to deploy code into Openshift. What we can do is to use another container to accomplish this task. The candidate I'll choose is the [Jenkins-Slave-Base](https://access.redhat.com/containers/?tab=overview#/registry.access.redhat.com/openshift3/jenkins-slave-base-rhel7) which is a minimal image which include those tools.


### How Do They Talk To Each Other

![](https://raw.githubusercontent.com/cesarvr/cicd/master/img/nodejs-3.PNG)

This is another advantage of pods is that containers running inside them can share resources, in the particular case of the Kubernetes Plugin, containers running inside share the same Jenkins ``workspace`` so they both can see the same folder.


This example we can see both containers collaborating:


```java
def NODEJS_IMAGE = '  '
def NODEJS_CONTAINER_NAME = 'nodejs'

def OC_CLIENT_IMAGE = "registry.redhat.io/openshift3/jenkins-slave-base-rhel7:v3.11"

def JNLP_CONTAINER = 'jnlp'

podTemplate(cloud:'openshift', label: BUILD_TAG,

  volumes: [configMapVolume(configMapName: "hello-es", mountPath: "/my-config")],

  containers: [

      /*
        Container with Node 12
      */

      containerTemplate(name: NODEJS_CONTAINER_NAME, image: NODEJS_IMAGE,
       ttyEnabled: true,
       command: 'cat'),

       /*
         Container with the oc-client
       */
       containerTemplate(name: "jnlp", image: OC_CLIENT_IMAGE)

  ] ) {

    node(BUILD_TAG) {

        container(NODEJS_CONTAINER_NAME) {
            stage('Building Node 12') {
                sh "node -v"
                git 'https://github.com/cesarvr/hello-world-nodejs.git'
                sh "npm install"
                sh "oc version || true"
            }
        }

        container(JNLP_CONTAINER) {
            stage('Building Node 12') {
                sh "ls -lart"
                sh "oc version || true"
            }
        }

    }
}

```

> The name of the second container ``jnlp`` has a special meaning to Jenkins, it means that this container has a Jenkins Agent (this will reduce the [amount of container running](https://github.com/cesarvr/cicd#what-happened)).

Let's take a look at the execution:

```sh
### Start: nodejs containner

#> git checkout -b master 9d5b5bad2efdbddd15f04d922ceef646036594e7
#Commit message: "fix"
# > git rev-list --no-walk 9d5b5bad2efdbddd15f04d922ceef646036594e7 # timeout=10
#[Pipeline] sh
#[test] Running shell script
+ npm install

[test] Running shell script
+ oc version
/home/jenkins/workspace/ctest/test@tmp/durable-995cdffc/script.sh: line 2: oc: command not found
+ true

### End: nodejs containner

### Start: jnlp containner

-rw-r--r--. 1 default 1051760000 229 Mar  2 15:58 package.json
-rw-r--r--. 1 default 1051760000  89 Mar  2 15:58 app.js
drwxr-sr-x. 8 default 1051760000 162 Mar  2 15:58 .git
-rw-r--r--. 1 default 1051760000  68 Mar  2 15:58 package-lock.json

Server https://172.30.0.1:443
openshift v3.11.43
kubernetes v1.11.0+d4cacc0

### End: jnlp containner
```
> Both containers can see the same workspace folder but each container has its own tools (you can see how the NodeJS failed to locate the ``oc-client``).


### Permissions

In order to deploy applications we should have a quick review to [service account](https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/). We can think of [service accounts](https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/) as a user for pod's. Any new pod gets a user called ``default`` which has minimum permissions to get itself up and running.

But we want to change the state of Openshift (create a container), so this permissions are not enough for that. The good news is that Jenkins creates a service account ``jenkins`` for this purposes. 

So let's pass this account to our pod: 

```java
podTemplate(cloud:'openshift', label: BUILD_TAG, serviceAccount: 'jenkins')
```

And now the final result we have a Jenkins build with two containers one running all NodeJS workload, the other push the build to a container:

```java
def NODEJS_IMAGE = 'docker-registry.default.svc:5000/openshift/nodejs:10'
def NODEJS_CONTAINER_NAME = 'nodejs'

def OC_CLIENT_IMAGE = "registry.redhat.io/openshift3/jenkins-slave-base-rhel7:v3.11"
def JNLP_CONTAINER = 'jnlp'

podTemplate(cloud:'openshift', label: BUILD_TAG, serviceAccount: 'jenkins',

  volumes: [configMapVolume(configMapName: "hello-es", mountPath: "/my-config")],

  containers: [

      /*
        Container with Node 12
      */
      containerTemplate(name: NODEJS_CONTAINER_NAME, image: NODEJS_IMAGE,
       ttyEnabled: true,
       command: 'cat'),

       /*
         Container with the oc-client
       */
       containerTemplate(name: "jnlp", image: OC_CLIENT_IMAGE)

  ] ) {

    node(BUILD_TAG) {

        container(NODEJS_CONTAINER_NAME) {
            stage('Building Node 12') {
                sh "node -v"
                git 'https://github.com/cesarvr/hello-world-nodejs.git'
                sh "npm install"
                sh "oc version || true"
            }

            /* Nodejs packaging/testing */
        }

        container(JNLP_CONTAINER) {
            stage('Creating Image') {
                sh "oc new-build ${NODEJS_IMAGE} --name=frontend --binary=true || true"
                sh "oc start-build bc/frontend --from-file=. --follow"
            }

            /* Deploy the container ... */
        }

    }
}
```

> The good thing about we can reuse the code inside ``JNLP_CONTAINER`` for other frameworks or languages.


At the end I'm impressed on how powerful this plugin and how easy is to simplify builds with this. Somebody asked me some days ago *"How can he do a [quarkus](https://quarkus.io/) pipeline in Openshift?"* I hope this post helps him solve that problem and inspire you guys to create really sophisticated, and more important, easy to maintain builds.