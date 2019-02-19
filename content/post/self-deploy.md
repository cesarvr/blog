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
image: https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/static/logo/js.png
---

Few days ago I was watching a [tech talk](https://www.youtube.com/watch?v=XPC-hFL-4lU) given by [Kelsey Hightower](https://twitter.com/kelseyhightower) with the title “Self Deploying Kubernetes Applications”, the talk is a bit old now (over a year), but I though is still interesting, so in this talk he was showcasing a [Golang](https://golang.org) HTTP server program, which at first seems like a typical hello world echo server, nothing special, but then he adds a new library and executes the program again, this time the program is magically running in the cloud as if Kubernetes was just an extension of his laptop OS.

<!--more-->

I think this is how developing cloud applications should be, instead of copy/pasting/modifying configuration files or entering complex commands, things should be as simple as to write a program, pass a flag as arguments indicating we want our snowflake running in the cloud.

Inspired by this I decided to write module that magically handle this, and to make it in a reasonable amount of time I used technology I'm familiar with like *JavaScript/Node.JS* and *OpenShift* (Red Hat Kubernetes) to handle the compute nodes. The objective, is that by including this module in your Node.JS your program can execute in your laptop OS or *OpenShift OS*.


### Simple HTTP Server

The best way to explain this is be seeing it working, so let's start by writing a simple web server:

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
In this 9 lines we got define a HTTP/Server listening in Port 8080, we serve a webpage showing an update registry of visitors and the OS platform where our application is running.

We save this file as ``app.js`` and run it locally:

```sh
  node app   # app.js
```

![](https://github.com/cesarvr/hugo-blog/blob/master/static/self-deploy/self-deploy-before.gif?raw=true)


Our application is running well, I think it's time to make a deploy this application in a remote computer.

### Self Deploying
<BR>

#### Setup
Next you'll need an OpenShift cluster up and running, you can one by getting access to [OpenShift Online](https://manage.openshift.com/) for free or setup one in your computer via [Minishift](https://github.com/minishift/minishift) or [oc cluster-up](https://github.com/cesarvr/Openshift#ocup).

Once you have OpenShift sorted out, you'll need to create a project/namespace manually, you can do this by login into the console and clicking into new project, thats the only limitation of the module at the moment at the moment is that it require a user with projects assigned to him.

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

Then it will show you the namespaces available for your user to chose :

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

> You don't need to delete your project before starting a new one, you can just continuing using --cloud options to override existing images.

Hope this module simplify a bit your life when developing micro-services using Node.JS, also you can contribute to [this module](https://github.com/cesarvr/okd-runner) by suggesting improvement or by opening an [issue](https://github.com/cesarvr/okd-runner/issues) or sending PR.  
