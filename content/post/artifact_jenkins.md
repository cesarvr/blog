---
title: "Jenkins Tricks On Openshift"
date: 2020-05-12T16:58:19+01:00
draft: false
tags: [openshift, build, cheatsheet]
---
<!--more-->

## Simplifying Builds

After more experimentation Jenkins Kubernetes plugin which allows to run Jenkins [to run build using containers as Jenkins Slave](https://cesarvr.io/post/jenkins-container/) I have found that you don't need to spin up a [Jenkins slave container](https://catalog.redhat.com/software/containers/detail/581d2f3f00e5d05639b6515b) to have access to Jenkins default tools (like running jobs, scm, etc) you can just run those commands in the *current node*.


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
            My source code requires Node:12 to build, so I checkout the repository.
        */
        stage('Clone Repository'){
            checkout scm
        }

        /*
          And use a Node:12 image to build the code.
        */
        container(NODE_12) {
          stage('Testing Deployment') {
            sh "npm install && npm test"
          }
        }
      }
    }
```
> ``Node:12`` shares the workspace with Jenkins.

## Pulling Artifacts From Other Builds

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
