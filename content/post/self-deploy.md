---
title: "Writing Self Deploying Node.JS Applications"
date: 2019-02-11
lastmod: 2019-02-18
draft: false
keywords: []
description: "Let's write an application that runs itself into OpenShift."
tags: [openshift, container, services, kubernetes]
categories: [openshift, container, nodejs, kubernetes]
toc: true
image: https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/static/logo/profiler.png
---

A few days ago I was watching [tech talk](https://www.youtube.com/watch?v=XPC-hFL-4lU) given by [Kelsey Hightower](https://twitter.com/kelseyhightower) with the title "Self Deploying Kubernetes Applications", the talk has over a year now but it was very interesting.

In this talk he was showcasing a typical [Golang](https://golang.org) server program, which at first seems like a typical *hello world* echo server, but then for my surprise he edit the source code, added a library and runs the program again which runs but this time it gets *magically deployed* into a Kubernetes cluster.

<!--more-->


The cool thing is that all the complexity behind that magic trick is hidden behind a simple interface (a simple module) freeing the developer from understanding Kubernetes idiosyncrasies. When I finish the video, I was convince that I have to write my own self-deployment mechanism, but it have to be for OpenShift because I'm not familiar *yet* with Google Cloud Kubernetes and this self-deploy mechanism will work with *one of my favorite* language *JavaScript*.


### Simple HTTP Server

So let's write and deploy a simple Node.JS HTTP server:

```js
let count = 0
require('http')
    .createServer((req, res) => {
        res.end(`<HTML>
                    <h1>Hello From -> ${process.platform}</h1>
                    <h2>Visitor: ${count++} </h2>
                </HTML>`)
        console.log(`response: ${Date.now()}`)
    }).listen(8080)
```

Here we create and setup an HTTP server that will listen in the TCP/Port **8080**, when a new client arrive we are going to serve a rudimentary webpage showing the operative system and the visitors count, all this awesomeness in 9 lines.

Now we save this file as ``app.js`` and run it locally to see how it goes:

```sh
  node app
```

![](https://github.com/cesarvr/hugo-blog/blob/master/static/self-deploy/before.gif?raw=true)


Our application is running well, I think it's time to make a deploy this application in somebody else computer AKA *the cloud*.

### Self Deploying
<BR>
#### Setup
Now this guide assume you got an OpenShift cluster up and running, if you don't, you still can get access to [OpenShift Online](https://manage.openshift.com/) for free or setup one in your computer via [Minishift](https://github.com/minishift/minishift) or [oc cluster-up](https://github.com/cesarvr/Openshift#ocup).

Once you have OpenShift sorted out, you'll need to create a project/namespace manually, you can do this by login into the console and clicking into new project, thats the only limitation of the module at the moment of not being able to create it for you.

#### OKD-Runner

After all that, we get back to our working directory and install ``okd-runner`` [module from npm](https://www.npmjs.com/package/okd-runner):

```sh
npm install install okd-runner --save
```

We require the module:

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

And run our application with the ``--cloud`` flag:


```sh
  node app.js --cloud   # or -c for short
```

The first time it will ask you for your cluster credentials:

![](https://github.com/cesarvr/hugo-blog/blob/master/static/self-deploy/creds.gif?raw=true)


#### Namespace, Container Creation & Deployment

Then it will show you the namespaces available for your user, you chose one:

![](https://github.com/cesarvr/hugo-blog/blob/master/static/self-deploy/deploy.gif?raw=true)

The next stage will create and deploy you image, once the image is deployed a route is created, as you might observe now the OS is Linux.


#### Routing

The route basically will allow traffic to your pod from the outside, when this components is created you will get the URL back:

```sh
...
building  ok
URL:  http://my-app-dev-01.7e14.starter-us-west-2.openshiftapps.com
...
```

#### Container Logs

Another convenient feature is to receive the logs of your container in your stdout, this makes your life easier to see what happening inside the container.

```sh
...
npm info using node@v10.14.0
npm info lifecycle my-app@1.0.0~prestart: my-app@1.0.0
npm info lifecycle my-app@1.0.0~start: my-app@1.0.0

> my-app@1.0.0 start /opt/app-root/src
> node app.js

response: 1550511176623
...
```


### Clean up

If you want to remove that project from the namespace you just need to execute your application with the ``-rm`` flag:

```js
node app -rm
```

This command will remove the project and all the generated components from OpenShift.

Hope this module simplify a bit your life when developing micro-services using Node.js, also you can contribute to [this module](https://github.com/cesarvr/okd-runner) by suggesting improvement or by opening an [issue](https://github.com/cesarvr/okd-runner/issues) or sending PR.  
