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

A year ago by now, I was [watching Kelsey Hightower](https://www.youtube.com/watch?v=XPC-hFL-4lU) giving a tech talk, in this talk he was showcasing a typical [Golang](https://golang.org) server program, at first it seems like a typical *hello world*, but then he close the program and edits the source code and add a library to the code, just a simple line, then he runs the program again the program gets magically deployed into Kubernetes cluster.

The cool thing about this is how simple it is from the point of view of the developer, basically all the technology behind that magic trick is completely abstracted behind a simple interface (adding a library) and freeing the developer of all the complexity and tools needed to achieve this. This motivate me to write my own self-deployment module, but it have to be for OpenShift (I more familiar with this flavor of Kubernetes) and I have to use JavaScript/Node.js. So let's see this library in action.

## Hello World...

To show you how it works let's write a simple Node.js HTTP server:

``js
let count = 0
require('http')
    .createServer((req, res) => {
        res.end(`<HTML>
                    <h1>Hello From -> ${process.platform}</h1>
                    <h2>Visitor: ${count++} </h2>
                </HTML>`)
        console.log(`response: ${Date.now()}`)
    }).listen(8080)
``

This is a typical Node.js server, we open an TCP/HTTP port in 8080 and wait for clients, if a clients connect we increment the visitors count and send a greetings page with an identifier of the server operative system and the visitors count.

Now we save this file as ``app.js`` and lets test this local:

```sh
  node app
```

![](https://github.com/cesarvr/hugo-blog/blob/master/static/self-deploy/before.gif?raw=true)


Nice, I think we are ready to make a container with JS/Node.js interpreter and the content of our working folder, and we want to deploy this container in machine that belong to somebody else aka the cloud.

## Cloud Runtime

Now this guide assume you got an OpenShift cluster up and running, if you don't you can get [OpenShift Online](https://manage.openshift.com/) for free or setup  [Minishift](https://github.com/minishift/minishift) or [oc cluster-up](https://github.com/cesarvr/Openshift#ocup).

Once you get OpenShift by any of those options, you need to create a project manually, you can do this by login into the console and clicking into new project, after that you just need to install ``okd-runner`` [module from npm](https://www.npmjs.com/package/okd-runner).

```sh
npm install install okd-runner --save
```

Add this library to the source code:

```js
let count = 0
const run = require('okd-runner') // <- self-deploy module
require('http')
    .createServer((req, res) => {
        res.end(`<HTML>
                    <h1>Hello From -> ${process.platform}</h1>
                    <h2>Visitor: ${count++} </h2>
                </HTML>`)
        console.log(`response: ${Date.now()}`)
    }).listen(8080)
```

And run your application with the ``--cloud`` flag:


```sh
  node app.js --cloud   # or -c for short
```

The first time you will see a prompt asking for your cluster credentials and namespace:

![]()



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
