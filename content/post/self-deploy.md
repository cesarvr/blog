---
title: "Self Deploying Node.JS Applications"
date: 2019-02-20
lastmod: 2019-02-20
draft: false
keywords: []
description: "Let's write an application that runs itself into OpenShift."
tags: [openshift, container, services, kubernetes]
categories: [openshift, container, nodejs, kubernetes]
toc: true
image: https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/static/logo/js.png
---

Few days ago I was watching in [Youtube a talk](https://www.youtube.com/watch?v=XPC-hFL-4lU) given by [Kelsey Hightower](https://twitter.com/kelseyhightower) titled "Self Deploying Kubernetes Applications". In this talk which is a bit old now (over a year) he was demoing a [Golang](https://golang.org) application capable of running locally but also capable of *magically* deploy itself into a Kubernetes cluster.

<!--more-->

This is how deploying applications into the cloud should be instead of copy/pasting/modifying configuration files or issuing cryptic commands, it should be as simple as it is running a process in our laptop. So after watching the talk I started to think on how to achieve this with one of my favorite programming language Javascript/Node.JS.

So after a few days of hacking with Kubernetes/OpenShift REST API, I wrote a small module that when imported ( or required) in a Node.JS application it extends its runtime capabilities allowing it to run in OpenShift (at the moment) by just adding a flag ``--cloud``. From the point of view of a non-expert it will looks like OpenShift is just another global JavaScript interpreter.

## Hello World

Let's see how this works by writing a simple web server:

```js
let count = 0
console.log('Running...')
require('http')
    .createServer((req, res) => {
        res.end(`<HTML>
                    <h1>Hello From -> ${process.platform}</h1>
                    <h2>Visitor: ${count++} </h2>
                </HTML>`)
        console.log(`response: ${Date.now()}`)
    }).listen(8080)
```
In this 9 lines we defined a HTTP/Server listening in Port 8080, serving a webpage that shows a counter with the visitors and the OS platform so we can see what OS is running our script.

We save this file with the name ``app.js`` and run test it locally:

```sh
  node app   # app.js
```

![](https://github.com/cesarvr/hugo-blog/blob/master/static/self-deploy/self-deploy-before.gif?raw=true)


<BR>

### Getting Started

Before continue you'll need an OpenShift cluster up and running, the easiest way is to subscribe here [OpenShift Online](https://manage.openshift.com/) for free or if you *feel strong* you can setup one in your computer via [Minishift](https://github.com/minishift/minishift) or [oc cluster-up](https://github.com/cesarvr/Openshift#ocup).

Once you have OpenShift sorted out, you'll need to create a project/namespace manually, you can do this by login into the web console and clicking into new project.

![](https://github.com/cesarvr/hugo-blog/blob/master/static/self-deploy/making-project.gif?raw=true)

<BR>
### Self Deploying

Now we should get back to our working directory and install ``okd-runner`` [module from npm](https://www.npmjs.com/package/okd-runner), this is the module that does the *magic*:

```sh
npm install install okd-runner --save
```

We add the module:

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

Adding the module won't affect directly at the code, meaning that you can continue running your application locally, the only difference is that you can choose a different execution runtime by passing the ``--cloud`` flag like this:

```sh
  node app --cloud   # or node app -c for short
```

We your application deploys the first time it will ask you for your cluster credentials:

![](https://github.com/cesarvr/hugo-blog/blob/master/static/self-deploy/creds.gif?raw=true)


And choose your namespace/project where you want to install your application:

![](https://github.com/cesarvr/hugo-blog/blob/master/static/self-deploy/deploy.gif?raw=true)


### Runtime

After that your application will deploy itself:

```sh
...
building  ok
URL:  http://my-app-dev-01.7e14.starter-us-west-2.openshiftapps.com
...
...
npm info using node@v10.14.0
npm info lifecycle my-app@1.0.0~prestart: my-app@1.0.0
npm info lifecycle my-app@1.0.0~start: my-app@1.0.0

> my-app@1.0.0 start /opt/app-root/src
> node app.js

response: 1550511176623
...
```

Here you can see the logs of you container plus the URL, to exit you just need to press ``Ctrl-C`` and you will get back to your console.

### Updating

From now everything is similar as to run your application locally, let's add a line of code to get the pods name and this way showcase how we can make an update:

```js
let count = 0
const run = require('okd-runner')
console.log('listening in 8080')
require('http')
    .createServer((req, res) => {
        res.end(`<HTML>
                    <h1>Hello From ${process.platform}</h1>
                    <h2>Visitors ${count++} </h2>
                    <!-- this line -->
                    <p>Pod ${require('os').hostname()}<p>
                </HTML>`)
        console.log(`response: ${Date.now()}`)
    }).listen(8080)

```

We run our application again:

```sh
  node app --cloud
```

This time it goes straight to deployment.

![](https://github.com/cesarvr/hugo-blog/blob/master/static/self-deploy/oc-update.gif?raw=true)


### Clean up

To remove your application you just need to pass the ``-rm`` flag:

```js
node app -rm
```


You see not a single YML file, hope this module helps you simplify your workflow while developing Node.JS micro-services. Also this module is still under development so feel free to [contribute](https://github.com/cesarvr/okd-runner) by sending suggestions, pull request, improvements or by opening an [issue](https://github.com/cesarvr/okd-runner/issues).  
