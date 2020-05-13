---
title: "Jenkins Tricks On Openshift"
date: 2020-05-12T16:58:19+01:00
draft: false
tags: [openshift, build, cheatsheet]
---
<!--more-->

## Simplifying Container Builds

I [discover recently](https://cesarvr.io/post/jenkins-container/) that you can use containers to run your builds. What I didn't know was that you can use the default Jenkins container ``jnlp`` to do some pre-build task, like cloning the project.


```js

podTemplate(
    cloud: 'openshift',
    label: BUILD_TAG,
    serviceAccount: 'jenkins',
    containers: [
    containerTemplate( name: NODE_12, image: NODE_12_IMAGE,
      ttyEnabled: true, command: 'cat') {
        
      node(BUILD_TAG) {
        /*
            You can run typical Jenkins instructions here, like checkout the branch.
        */
        stage('test'){
            checkout scm
        }

        /*
            The result of cloning are mounted into the Node:12 container
             to continue the build on that image.

        */
        container(NODE_12) {
          stage('Testing Deployment') {
            sh "npm install && npm test"
          }
        }
      }
    }
```

> Until now I always override the Jenkins slave with [this image](https://catalog.redhat.com/software/containers/detail/581d2f3f00e5d05639b6515b), without knowing that this is running by default.


## Pulling Artifacts From Builds

They are special situation when I need to pull **artifacts** from Jenkins, so I end up writing this small Jenkins DSL to fetch assets from other builds.  



```js
def Artifact = "https://jenkins-server/.../lastSuccessfulBuild/artifact/target/artifact.jar"

/*
  boilerplate...
*/
stage('Fetching Artifact') {
  //We get the Jenkins service account token.
  def token = sh (script: "oc whoami -t", returnStdout: true).trim()

  /*
  /* Because we don't want to display the token: set +x
  /* We send a GET request with the token on the HTTP Header
  */
  sh "set +x && curl -O -H \"Authorization: Bearer ${token}\" -k ${Artifact}"

  //The artifact is downloaded.
  sh "ls -alrt"
}

/**/
```
