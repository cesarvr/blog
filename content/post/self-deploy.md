---
title: "Self-Deploying Node.JS Applications"
date: 2018-12-11
lastmod: 2018-12-11
draft: true
keywords: []
description: "How to write application that deploy themselves in the cloud."
tags: [openshift, container, services, kubernetes]
categories: [openshift, container, nodejs, kubernetes]
toc: true
image: https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/static/logo/profiler.png
---

A couple of months ago I was [watching Kelsey Hightower](https://www.youtube.com/watch?v=XPC-hFL-4lU) giving a talk where he was showing a typical [Golang](https://golang.org) server program, not big deal, then he close the program open the source code with vim and add a new library to the code just a simple line, now when he runs the program again it magically gets deployed into Kubernetes that simple.

No need to know the underlaying complexity of the container orchestration platform, this simplicity was my inspiration to write my own Node.js self-deployment library which I call [okd-runner](), the **okd** part is because at the moment only works with OpenShift (Red Hat Kubernetes distribution) because I'm more familiar with it, but I have plans to port it to Kubernetes.

## Hello World...

To show you how it works let's write a simple Node.js HTTP server:

``js
const http = require('http')
const port = '8080'
const app = new http.Server()

app.on('request', (req, res) => {
  console.log('request: ', Date.now())
  res.writeHead(200, { 'Content-Type': 'text/plain' })
  res.end('Hello World \n')
})

app.listen(port, () =>  console.log(`Listening on port ${port}`) )
``

This is a typical Node.js server, we open an TCP/HTTP port in 8080, subscribe to ``request`` events and we respond with a simple HTTP *200* header and a ``hello world`` message in the body.


## Testing Locally

We save this file let's called ``app.js`` and we execute it this way.

```sh
  node app.js

  Listening on port 8080
  receiving a request:  1550488478558
  receiving a request:  1550488478578
```

## Cloud Deployment

Assuming you have free OpenShift or an instance like [OpenShift Online](https://manage.openshift.com/), you can install a some local alternatives like [Minishift](https://github.com/minishift/minishift) or [oc cluster-up](https://github.com/cesarvr/Openshift#ocup).


Once you get OpenShift up and running you can proceed to deploy your application by doing:

```sh
npm install install okd-runner --save
```

Now just add this library to the source code:

```js
const http  = require('http')
const runner = require('okd-runner')
const port  = '8080'
const app   = new http.Server()

app.on('request', (req, res) => {
  console.log('request: ', Date.now())
  /*...*/
})
  /*...*/
```

And run your application like this:


```sh
  node app.js -c
```


After you execute this command you will be prompted with your OpenShift login cluster URL and login credentials and you should choose a namespace (*the namespace is just a project name, you need to create one manually using the web console*) then you are ready to go.  

![]()


## What just have Happened ?

This command basically take your working folder and make a container using OpenShift Node.JS images and the deploy this image and setup the traffic for your application. Also as you might see at end of the animation, you can see the logs of your container in real-time this will also help you debugging any issues, once you finish you just need to press ctrl-c and you will return return to your shell but your application will keep running in the cloud.  

## Clean up

If you want to remove that project from the namespace you just need to run your application in local using the ``-rm`` flag:

```js
node app -rm
```

This command will remove the project and the image streams from OpenShift.


Hope this module simplify a bit your transition to the development container applications using Node.js, also this module is open source, so feel free to contribute with any improvement or change just send a PR.  
