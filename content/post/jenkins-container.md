---
title: "Decoupling Jenkins Builds In Openshift"
date: 2020-02-17T18:37:00Z
draft: false
---

I was given the task to help my co-workers understand and take advantage of the Openshift container platform (based on Kubernetes). So I decided to write some guides on how to automate y applications deployments. One of those guides was a minimal getting started Jenkins guide that looks something like this:

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

This was very welcome by the teams but as soon as they started to implement this they started to face challenges. A team in particular was trying to develop something in Angular 8 which required minimum Node 10 and as you can see in the logs the official supported version in Openshift is 8. Also they found it challenging to add configuration files, they tried setting this up on Jenkins, but usually if you are using this type of workflow the Jenkins created for you is ephemeral (not persisted) this mean lost all the configuration if Jenkins get re-deploy.  

So after all this good feedback I started to research for a ways to improve this with an alternative that target the following characteristics:

* It should be flexible. I don't want teams customizing their own images (if not strictly necessary), because this add a maintenance overhead and Dockerfile can become a nightmare to maintain when they get bigger.

* Easy to customize. Adding a configuration file or storage to a build should be defined in the Jenkins DSL.       

* Composable: Use the best container image for the job.

* I need to be as simple as possible. No dockerfile and no black-magic (like installing NVM at runtime).

## Jenkins Kubernetes Plugin

Was by doing this that’s how I discovered the *Kubernetes Jenkins Plugin*, which until that moment I didn’t know it was this plugin that was doing all the calls to Openshift behind the scenes for the first example. After some reading I discovered that you can define, not only how your software gets build but also their infrastructure (the *pods* running your build).

The [pod](https://kubernetes.io/docs/concepts/workloads/pods/pod/) its a Openshift/Kubernetes entity that can be thought as a container with more containers inside and this is interesting because it encourage the isolation of concerns (like objects in OOP) while sharing common resources provided by the pod -- i.e., you can handle *NodeJS* task such as dependencies and  testing in a ``NodeJS:10`` container and delegate other task such as deployment to another container (one with [oc-client](https://github.com/openshift/origin/releases) for example).


#### Defining The Pod

To define our *container of containers* we use this function:

```java
podTemplate(cloud:'openshift', label: BUILD_TAG,  containers[/*...*/], /*...*/ )
```
Where:

* ``cloud`` This should point to the Kubernetes configuration, if you are running this in Openshift is ``openshift`` is created by default.
* ``label`` is a way to identify the pod, this allows the plugin to locate your pod in the cluster.
* ``container`` is an array of container objects, you can define containers using ``containerTemplate`` as explained below.

> Here you define settings that have a global influence over the containers running inside.

#### Running Containers

To define container(s) inside the pod we use:

```java
containerTemplate(name: ‘’, image: ‘’, /*...*/ )
```

Where:

- ``name`` The container name.
- ``image`` The image that you need to instantiate the container.

 > For more information you can [visit Kubernetes Plugin](https://github.com/jenkinsci/kubernetes-plugin).

> And here we target the specifics like I need ``maven:3.2``.

## Hello World

In the example above we hit that limitation because we are using the pre-defined [NodeJS-Jenkins-Agent](https://access.redhat.com/containers/#/registry.access.redhat.com/openshift3/jenkins-agent-nodejs-8-rhel7) that comes out-of-the-box in Openshift. To overcome this we are going to define our own Jenkins worker pod.

First let's look for an image that support Angular 8:

```sh
oc get is -n openshift | grep node
#nodejs docker-registry.default.svc:5000/openshift/nodejs 10,4,6 + 4
```

> You can get your cluster admin to create/update the image stream for [Node:12](https://access.redhat.com/containers/#/registry.access.redhat.com/rhel8/nodejs-12) if you want to target the [LTS](https://nodejs.org/en/).

We can see that the ``nodejs:10`` is the supported image so let's work with that and write a Jenkins file like this one:

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

> The ``command:cat`` and ``ttyEnabled`` is just a small hack to avoid a race condition between Jenkins and the container,  this will block the container until Jenkins logs into the container and execute the job.   

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

Nice we don't longer need to wait for Red Hat to update their NodeJS Jenkins slave and the team can use any official image to accomplish for their builds, let's see how do we deal with state.

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

## Composable

Now this getting interesting, sometimes having the right version of the framework is not enough, in the example above for example Node-10 doesn't have the tools to deploy code into Openshift. What we can do is to use another container to accomplish this task. The candidate I'll choose is the [Jenkins-Slave-Base](https://access.redhat.com/containers/?tab=overview#/registry.access.redhat.com/openshift3/jenkins-slave-base-rhel7) which is a minimal image which include those tools.




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

Let's take at the execution:

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
> They can see the same workspace folder but each container has its own tools (you can see how the NodeJS failed to locate the ``oc-client``).


### Permissions

Openshift implements a permissions system based on [service accounts](https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/). The good news is that Jenkins creates a service account called ``jenkins`` in its first start, this account (after user validation) allows Jenkins to operate in the current namespace. We just need to pass this account to our pod and it will inherit those permissions.

We can provide the service account like this:

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

At the end I'm impress on how powerful this plugin is, somebody ask me some days ago How can he do a [quarkus](https://quarkus.io/) pipeline in Openshift? I hope this post helps him solve that problem and inspire you guys to create really sophisticated and more important simpler to maintain builds.  
