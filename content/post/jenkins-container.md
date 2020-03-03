---
title: "Decoupling Jenkins Builds In Openshift"
date: 2020-02-17T18:37:00Z
draft: false
---

I was given the task to help my co-workers understand and take advantage of the Openshift 3.11 container platform which is based on Kubernetes. So I decided to write some guides on how to deploy applications and how to do it automatically.

One of this guides was to write a minimal get started Jenkins guide that looks something like this:

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

This was very welcome by the teams, but as soon as they started to implement this they started to ask for changes. A team in particular was trying to develop something in Angular 8 which means they needed Node 10+ minimum and as you can see in the logs the official supported version in Openshift is 8. Also they found it challenging to add configuration files, they have to setup this on Jenkins and if this Jenkins is not persisted then they will lost all the configuration.  

So I started to research for a way to make this better aiming for the following goals:

* It should be flexible. I don't want teams customizing their own images (if not strictly necessary), because this add a maintenance overhead and Dockerfile can become a nightmare to maintain when they get bigger. 

* Easy to customize. Adding a configuration file or storage to a build should be defined in the Jenkins DSL.       

* Composable: Use the best container image for the job.

* I need to be as simple as possible. No dockerfile and no black-magic (like installing NVM at runtime).

## Jenkins Kubernetes Plugin

That’s how I discovered the *Kubernetes Jenkins Plugin*, which until that moment I didn’t know it was this plugin that was doing all the calls to Openshift behind the scenes for the first example. So after some reading the documentation I discovered that you can define not only how your software gets build but also their infraestructure (the *pods* running your build).

A [pod](https://kubernetes.io/docs/concepts/workloads/pods/pod/) is an Openshift/Kubernetes abstraction that encapsulates one or more containers. The pod itself can be thought as a container with more containers inside, this is interesting because we can use the containers inside to encapsulate knowledge (like objects in OOP) -- i.e., you can handle Node dependencies/testing in a *Node-10* container and delegate the deployment to another container (one with [oc-client](https://github.com/openshift/origin/releases) for example).  

#### Defining The Pod

To define our container of containers we use this function:

```java
podTemplate(cloud:'openshift', label: BUILD_TAG,  containers[/*...*/], /*...*/ )
```
Where: 

* ``cloud`` This should point to the Kubernetes configuration, if you are running this in Openshift is ``openshift`` is created by default.
* ``label`` is a way to identify the pod, this allows the plugin to locate your pod in the cluster.
* ``container`` is an array of container objects, you can define containers using ``containerTemplate`` as explained below.

#### Running Containers

To define container(s) inside the pod we use:

```java
containerTemplate(name: ‘’, image: ‘’, /*...*/ )
```

Where:

- ``name`` The container name.
- ``image`` The image that you need to instantiate the container.


 > For more information you can [visit Kubernetes Plugin](https://github.com/jenkinsci/kubernetes-plugin).


## Hello World 

In this hello world we are going to overcome the Node 8, this limitation is only for the pre-defined Jenkins Agent that comes out-of-the-box in Openshift. By manipulating manually the Jenkins Plugin we can overcome this limitation and spin-up the container we want.

First let's look for an image that support Angular 8:

```sh
oc get is -n openshift | grep node
#nodejs docker-registry.default.svc:5000/openshift/nodejs 10,4,6 + 4
```

> You can get your cluster admin to create update the image stream for [Node:12](https://access.redhat.com/containers/#/registry.access.redhat.com/rhel8/nodejs-12). 

We can see that the ``nodejs:10`` is supported, this allow me to write the Jenkinsfile like this:

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

This is great we don't longer need to wait for Red Hat to update their NodeJS Jenkins slave, the team can use any official image to acomplish their task.

## Customizable

Another thing we wanted was to be able to customize the container running the job, let's see how we can introduce a *configuration file* via [Config Map](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/).


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

Now this method is very interesting sometimes having the right version of the framework is not enough, in the example above for example Node-10 doesn't have the tools to deploy my code into Openshift. But what we can do is to use another container to acomplish this task. The candidate I'll choose is the [Jenkins-Slave-Base](https://access.redhat.com/containers/?tab=overview#/registry.access.redhat.com/openshift3/jenkins-slave-base-rhel7) which is a minimal image which include those tools.

### How Do They Talk To Each Other 

This is another advatange of pods is that containers running inside them can share resources, in the particular case of the Kubernetes Plugin, containers running inside share the same Jenkins ``workspace`` so they both can see the same folder as you will see here: 


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
> They can see the same folder but each container has its own tools, just like Objects. 

Having the tools is not enough as Openshift implements a permissions system based on [service accounts](https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/). The good news is that Jenkins creates one in its first start called ``jenkins`` which allows Jenkins to operate in the current namespace. We just need to pass this account to our pod to inherith those permissions.

We can define the service account here:

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

            /* Deploy the container stages */
        }

    }
}
```

At the end I'm impress on how powerful this plugin is, somebody ask me some days ago How he can do a Quarkus pipeline in Openshift? I think he was asking the question basically because they where using the official Jenkins agent. Hope that with this guide he/you can overcome this limitation and create really interesting workflows.  


