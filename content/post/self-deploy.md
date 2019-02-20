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

Have you notice how complex is sometimes to deploy an application in the cloud ? 

<!--more-->


### Hello World

To watch how this module works let's write a simple web server:

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

Next you'll need an OpenShift cluster up and running, you can one by getting access to [OpenShift Online](https://manage.openshift.com/) for free or setup one in your computer via [Minishift](https://github.com/minishift/minishift) or [oc cluster-up](https://github.com/cesarvr/Openshift#ocup).

Once you have OpenShift sorted out, you'll need to create a project/namespace manually, you can do this by login into the console and clicking into new project.

![](https://github.com/cesarvr/hugo-blog/blob/master/static/self-deploy/making-project.gif?raw=true)


#### Deploying

Now should get back to our working directory and install ``okd-runner`` [module from npm](https://www.npmjs.com/package/okd-runner):

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

And run our application with the ``--cloud`` flag:


```sh
  node app.js --cloud   # or -c for short
```

The first time it will ask you for your cluster credentials:

![](https://github.com/cesarvr/hugo-blog/blob/master/static/self-deploy/creds.gif?raw=true)


#### Namespace, Container Creation & Deployment

You chose a namespaces:

![](https://github.com/cesarvr/hugo-blog/blob/master/static/self-deploy/deploy.gif?raw=true)

The next stage will create and deploy you image, once the image is deployed a route is created, as you might observe now the OS is Linux.

#### Getting Access

Once you application is deployed you will see logs of your container and the URL to access your application.

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


### Making A Change

Let's modify our application so we can observe what pod is handling the request:

```js
let count = 0
const run = require('okd-runner')
console.log('listening in 8080')
require('http')
    .createServer((req, res) => {
        res.end(`<HTML>
                    <h1>Hello From -> ${process.platform}</h1>
                    <h2>Visitor: ${count++} </h2>
                    <!-- this line -->
                    <p>${require('os').hostname()}<p>
                </HTML>`)
        console.log(`response: ${Date.now()}`)
    }).listen(8080)

```

To deploy this change in the cloud we just need execute the command again:


```sh
  node app --cloud
```

After the module cache your credentials, everything is more faster now.

![](https://github.com/cesarvr/hugo-blog/blob/master/static/self-deploy/oc-update.gif?raw=true)



### Clean up

If you want to remove that project from the namespace you just need to execute your application with the ``-rm`` flag:

```js
node app -rm
```

This command will remove the project and all the generated components from OpenShift.


You see not a single YML file, hope this module helps you simplify your workflow while developing Node.JS micro-services, you can [contribute](https://github.com/cesarvr/okd-runner) by suggesting improvement or by opening an [issue](https://github.com/cesarvr/okd-runner/issues) or by sending a pull request.  
