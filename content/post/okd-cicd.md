---
title: "Simple CI/CD"
date: 2018-07-21T11:18:43+02:00
showDate: false
draft: true
toc: true
description: Using chained builds to improve the size of your images and overall deployment performance in Openshift.
images:
  - https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
tags: [openshift, build]
---

Get your Java source code, tested, packaged, containerized and deployed in four steps. We are going to defined 4 decoupled steps that
you can improve with more complex use cases in the future. 

<!--more-->

Step One 

I'm going to start by defining how the container will be created in Openshift, so let's do this by defining a build configuration (AKA [BuildConfig](https://cesarvr.io/post/buildconfig/)):





