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



# Openshift Console

The easiest way to deploy your application is to go to the dashboard and just choose a template from the catalog: 

![deploying nodejs applications](https://github.com/cesarvr/Openshift/raw/master/assets/new-app-nodejs.gif?raw=true)





# Simplest  

The easiest way to deploy an application in Openshift is to use ```new-app```.

```sh
 oc new-app --name node-app nodejs~https://github.com/cesarvr/hello-world-nodejs
```















