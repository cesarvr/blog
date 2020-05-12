---
title: "Fetching Artifacts From Other Builds Jenkins/Openshift"
date: 2020-05-12T16:58:19+01:00
draft: false
tags: [openshift, build, cheatsheet]
---

They are special situation when I need to pull artifacts from Jenkins, so I end up writing this small Jenkins DSL to fetch assets from other builds.  

<!--more-->

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
