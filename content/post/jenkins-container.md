---
title: "Decoupling Jenkins Builds In Openshift"
date: 2020-02-17T18:37:00Z
draft: true
---


I was given the task to help my co-workers understand and take advantage of the Openshift 3.11 container platform which is based on Kubernetes. So I decided to write some guides on how to deploy applications and how to do it automatically.

One of this guides includes a minimal get started with Jenkins that looks like this:

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
    }
  }
}
```

Output:



This basically will spin up for you a container and automatically run your build inside a container allowing you, the user, to your builds parallel distributing the work across your nodes.


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

This was a welcome addition and received with vitors, but when the teams started to implement this they started to ask for changes. A team in particular was trying to develop something in Angular 8 which means they needed Node 10+ minimum and as you can see in the logs the official supported version from Red Hat is 8. Not only this but you will also want to have some persistence to avoid pulling Angular (almost a gigabyte) from the network over and over again. 


So I started to research for a way to make this better aiming for the following goals: 

* I should be able to exchange images, I don’t want that framework versions to be a problem. (as long as the image is provided by an official source (like Red Hat) it’s fine).

* Easy to customize. For example: Easy to add new storage in code or configuration files via Config Map.    
* Composable: Use the best container image for the job. 

* I need to be as simple as possible. No dockerfile and no version override at runtime.


## Jenkins Kubernetes Plugin

That’s how I discovered the *Kubernetes Jenkins Plugin*, which until that moment I didn’t know was the one doing all the calls to Openshift behind the scenes. So after reading the documentation I discovered that you can define with this plugin your own *pods*. 

A pod is an Openshift/Kubernetes abstraction that encapsulates one or more containers. The pod itself can be thought of as a container with more containers inside which is interesting because we can use the containers inside to encapsulate knowledge (like objects), this way we can have one container handling everything node related and other container doing the deployment task, but I'm getting ahead of myself.  
  
Before jumping to multiple containers collaborating with each other let’s see how this plugin API works: 

#### Pod 

```java
podTemplate(cloud:'openshift', label: BUILD_TAG,  containers[/*...*/], /*...*/ )
```

This function describes the pod, 

* ``cloud`` For the Kubernetes configuration, if you are running in Openshift is ``openshift`` is created by default for you.
* ``label`` is basically the pod identifier, pod names are random and they get destroyed and restarted without notice, this allows the plugin to locate them in the cluster. 
* ``container`` is an array of container objects, you can define containers using ``containerTemplate`` function explained below. 

#### containers

```java
containerTemplate(name: ‘’, image: ‘’, /*...*/ )
```

This function defines the container(s) running inside the pod.

- ``name`` The container name. 
- ``image`` The image that you need to instantiate the container.


 > For more information you can [visit Kubernetes Plugin](https://github.com/jenkinsci/kubernetes-plugin). 


## Version Idependent 

First thing I do is to look for an official image that support Node 10: 

```sh
oc get is -n openshift | grep node 
#nodejs docker-registry.default.svc:5000/openshift/nodejs 10,4,6 + 4
```

We can see that the ``nodejs:10`` is supported, this allow me to write the Jenkinsfile like this: 

```java
def NODEJS_IMAGE = 'docker-registry.default.svc:5000/openshift/nodejs:10'
def NODEJS_CONTAINER = 'nodejs'

podTemplate(cloud:'openshift', label: BUILD_TAG, 
  
  containers: [
      containerTemplate(name: NODEJS_CONTAINER, image: NODEJS_IMAGE, 
       ttyEnabled: true, 
       command: 'cat'),
  ] ) {
    
    node(BUILD_TAG) {
        
        container(NODEJS_CONTAINER) {
            stage('Hello World') {
                echo "build: " + BUILD_TAG
                sh 'node -v'
            }
            /* More stages */
        }
        
    }
}
```
> The ``command:cat`` and ``ttyEnabled`` is a small hack to keep the container running while waiting for the Jenkins job.   


Output:


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


Now we can choose any version of Node.JS available from the docker registry. 



## Customizable 

As mentioned before this plugin allow you to customize the container running the job, let's simulate introducing a file via Config Map. 

```sh
echo "Hola Mundo" >> hello.txt
oc create configmap hello-es --from-file=hello.txt
```

> This will create a file and configure a Config Map. 


Now let's add this *configuration file* to our build: 

```java
def NODEJS_IMAGE = 'docker-registry.default.svc:5000/openshift/nodejs:10'
def NODEJS_CONTAINER = 'nodejs'

podTemplate(cloud:'openshift', label: BUILD_TAG, 

  /* 
    We can attach the volumes here: 
      configMapVolume(configMapName:'', mountPath:'')
      persistentVolumeClaim(claimName:'', mountPath:'')
  */
  volumes: [configMapVolume(configMapName: "hello-es", mountPath: "/my-config")],

  containers: [
      containerTemplate(name: NODEJS_CONTAINER, image: NODEJS_IMAGE, 
       ttyEnabled: true, 
       command: 'cat')
  ] ) {
    
    node(BUILD_TAG) {
        
        container(NODEJS_CONTAINER) {
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

Now this method is very interesting sometimes having the right version of the framework is not enough we are going to need additional tools, like tools like ``oc-client`` which can deploy our code to Openshift. We can do this by using two images, treating them like objects: 

```java
def NODEJS_IMAGE = '  '
def NODEJS_CONTAINER = 'nodejs'

def OC_CLIENT_IMAGE = "registry.redhat.io/openshift3/jenkins-agent-nodejs-8-rhel7:v3.11"
def JNLP_CONTAINER = 'jnlp'

podTemplate(cloud:'openshift', label: BUILD_TAG, 
  
  volumes: [configMapVolume(configMapName: "hello-es", mountPath: "/my-config")],

  containers: [
      
      /*
        Container with Node 12
      */

      containerTemplate(name: NODEJS_CONTAINER, image: NODEJS_IMAGE, 
       ttyEnabled: true, 
       command: 'cat'),
       
       /*
         Container with the oc-client
       */
       containerTemplate(name: "jnlp", image: OC_CLIENT_IMAGE)
       
  ] ) {
    
    node(BUILD_TAG) {
        
        container(NODEJS_CONTAINER) {
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
> This is very interesting, we can use tools that are belong to each container, meaning that we have isolation. But also we see that both container share the same **workspace**, so we can take the packaged product of the **Node-12** and deploy it with the ``jnlp`` container. 


But there is a problem, even whe we have the tool we miss don't have the permission to do anything in this project. When Jenkins is created in Openshift the Kubernetes Plugins setup a ``jenkins`` service account that allow Jenkins to perform changes in the namespace. We just need to provide this user to our pod. 

```java
def NODEJS_IMAGE = 'docker-registry.default.svc:5000/openshift/nodejs:10'
def NODEJS_CONTAINER = 'nodejs'

def OC_CLIENT_IMAGE = "registry.redhat.io/openshift3/jenkins-agent-nodejs-8-rhel7:v3.11"
def JNLP_CONTAINER = 'jnlp'

podTemplate(cloud:'openshift', label: BUILD_TAG, serviceAccount: 'jenkins',
  
  volumes: [configMapVolume(configMapName: "hello-es", mountPath: "/my-config")],

  containers: [
      
      /*
        Container with Node 12
      */
      containerTemplate(name: NODEJS_CONTAINER, image: NODEJS_IMAGE, 
       ttyEnabled: true, 
       command: 'cat'),
       
       /*
         Container with the oc-client
       */
       containerTemplate(name: "jnlp", image: OC_CLIENT_IMAGE)
       
  ] ) {
    
    node(BUILD_TAG) {
        
        container(NODEJS_CONTAINER) {
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

> We add the service account ``podTemplate(/*..*/ serviceAccount: 'jenkins' `` This account is necessary to perform changes in the namespace. 

  





