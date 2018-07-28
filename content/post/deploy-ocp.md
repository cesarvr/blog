---
title: "Deploy Ocp"
date: 2018-07-28T19:24:19+01:00
lastmod: 2018-07-28T19:24:19+01:00
draft: false
keywords: []
description: ""
tags: []
categories: []
author: ""

# You can also close(false) or open(true) something for this content.
# P.S. comment can only be closed
comment: true
toc: false
autoCollapseToc: false
# You can also define another contentCopyright. e.g. contentCopyright: "This is another copyright."
contentCopyright: false
reward: false
mathjax: false
---

<!--more-->

They are multiple ways 



# Openshift console

The easiest way to deploy your application is to go to the dashboard and just choose a template from the catalog: 

![deploying nodejs applications](https://github.com/cesarvr/Openshift/raw/master/assets/new-app-nodejs.gif?raw=true)


# Using new-app  

The easiest way to deploy an application in Openshift is to use ```new-app```.

```sh
 oc new-app --name node-app nodejs~https://github.com/cesarvr/hello-world-nodejs
```

This command will create the same components as the openshift console with the omission of the router object, this need be created manually by calling the command ```oc expose```.    

```
oc expose svc <name-of-the-service>
```

![new-app](https://github.com/cesarvr/hugo-blog/blob/master/static/static/ocp-deploy/ocp-deploy.gif?raw=true)


Every time you write this two command Openshift will generate all the necessary objects to deploy your container and start directing to them, but there is a small inconvenience if you want to remove all the created objects let said you made a mistake you need to delete those one by one. But we are lucky that all the created objects share the same label, here is the command to clean those objects.    

```sh
 oc delete all -l app=node-app # this delete all the objects with label node-app
```

What I usually do is to create a sh function and save inside my bash.    

```sh
 function rm-app {
   oc delete all -l app=$1
 }

 # The I called this way: 
 rm-app node-app

 #deploymentconfig "node-app" deleted
 #buildconfig "node-app" deleted
 #imagestream "node-app" deleted
 #route "node-app" deleted
 #service "node-app" deleted
```





   















