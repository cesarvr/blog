---
title: "Creating Your Own Istio (Part 3)"
date: 2018-12-11
lastmod: 2018-12-11
draft: true
keywords: []
description: "Reusable Telemetry"
tags: [openshift, container, services, kubernetes]
categories: [openshift, container, services, kubernetes]
toc: false
image: https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/static/logo/profiler.png
---

In this post we are going to take our decorator container a step further and make it report the collected data to a centralize service, then we are going to make sense of this data by showing it with nice graphics.

<!--more-->

## Design

What we are going to do is actually very simple we are going to take the data we are collecting from the services running in the pod and we are going to send it to a central place for consumption.

### Refactoring

The previous post we wrote a class (*Stats*) that take care of persisting the data in memory, sample networking traffic and read hardware resources of our pod. Having this much functionality in a single class reduce the ways in which we can use the functionality, so let's do a quick refactoring to separate this into three components.

The first component will take care of reading the hardware telemetry:

```js
class Pod {
  constructor() {
    this.os = require('os')
  }

  host() {
    return this.os.hostname()
  }

  get resources() {
    return {
      free_memory: this.os.freemem(),
      total_memory: this.os.totalmem(),
      cpus: this.os.cpus()
    }
  }
}
```

Here we just copy/paste code form the *Stats* class into a new class.

Next step we are going to create a new class and move the in-memory store logic there.

```js
class DB {
  constructor(){
    this.db = []
  }

  save(obj){
    this.db.push( obj )
  }

  size(){
    return this.db.length
  }

  get all() {
    return this.db.map(obj => obj.sample)
  }
}

module.exports = { DB }
```

Again we just copy/paste from our previous example, but this time we use an array instead of an JavaScript object, also we modify the returning value in the ``all`` method, instead of returning a simple object, this class now assumes that we have objects that respond to the ``sample`` method/message call.


Last component we are going to reuse the *Stats* class, and simplify the way it collect and presents the data.

```js
class Stats {
  constructor() {
    this.close = false
  }
   isFile(endpoint){/*..*/}
   readResponse(response) {/*..*/}
   readRequest(header) {/*..*/}
   startProfile() {/*..*/}
   endProfile() {/*..*/}
   get sample() {
       return {
         endpoint: this.endpoint,
         method: this.method,
         response: this.response,
         time: this.end,
         started: this.start,
         file: this.isFile(this.endpoint),
       }
   }
 }
```

Here we just remove the history method and just used a mere plain JavaScript object. We are going to organize this three components as follows:

We put the classes `Pod` and `Stats` inside ``./monitor.js`` module:

```js
  class Pod   { /*...*/ }
  class Stats { /*...*/ }

  module.exports = {Stats, Pod}
```

And *DB* inside the ``./db.js`` module:

```js
  class DB   { /*...*/ }

  module.exports = {DB}
```

### Implementation

```js
const { Stats } = require('./monitor')

function telemetry({service, server}) {
  let stats = new Stats()

  server.on('http:data',  (header)       => stats.readRequest(header)
                                                 .startProfile())

  service.on('http:data', (header, data) => stats.readResponse(header, data)
                                                 .endProfile()
                                                 .finish())
}
```

To save each transaction we are going to create *DB* object.

```js
const { Stats, Pod } = require('./monitor')
const { DB } = require('./db')

let db = new DB()

function telemetry({service, server}) {
  let stats = new Stats()

  server.on('http:data',  (header)       => stats.readRequest(header)
                                                 .startProfile())

  service.on('http:data', (header, data) => stats.readResponse(header, data)
                                                 .endProfile()
                                                 .finish())
  db.save(stats)
}
```

Now we are in the same place as our last post, the difference now is that our system has more flexibility as you will see later.


### Making Sense Of Data

Collecting data from our pod is great, but our *"service mesh"* need to provide a way to make sense of the collected metrics. We can start by designing a *micro-service* that collect this metrics and show it in a human friendly way.

Our service will implement two endpoints and will receive the data in the following format:

```js
  {pod: '<name-of-the-pod>', data: 'body-of-statistics' }
```

Every decorator should identify the pod and the metric that is collecting. To identify what type of data we are collecting we are going to provide two endpoints one for service performance ``/stats`` another for the hardware telemetry ``/resources``.

#### Setup

Let's setup a new Node.JS project:

```sh
mkdir dashboard-project-folder && cd dashboard-project-folder
npm init
npm install -S express  #Install the express framework
```

##### Hello World

Here is the minimal amount of code required to create a Node.JS web service.

```js
const express = require('express')
const app = express()
const port = 8080

app.get('/',  (req, res) => {
  res.status(200).send({message: "Hello World"})
} )

app.listen(port, () => console.log(`Listening: ${port}!`))
```

We instantiate the [express framework](https://expressjs.com/) choose the port ``8080``, create a function to handle the HTTP GET request to the ``/`` endpoint and start a web server.

```sh
curl 0.0.0.0:8080
{"message":"Hello World"}%
```

##### Request

Your typical POST request has the following shape:

```xml
POST / HTTP/1.1
Host: foo.com
Content-Type: application/x-www-form-urlencoded
Content-Length: 13

pod=Hi&to=<a-lot-of-data>
```
It would be nice if we can transform the content (``pod=Hi&to=<a-lot-of-data>``) into a JSON object so is easier to work with, for that reason we are going to use ``body-parser`` library.

To install ``body-parser``:

```sh
 npm install -S body-parser
```

Implementation:

```js
const express = require('express')
const bodyParser = require('body-parser')
/*...*/
app.use(bodyParser.json())

app.get('/',  (req, res) => {
  res.status(200).send({message: "Hello World"})
} )

/*..*/
```

##### Persisting

To keep things simple we are going to persist the data using a dictionary.

```js
let stats = {}

app.post('/stats', (req, res)  => {
  let data = req.body

  stats[data.pod] = data

  console.log('data ->', data)
  res.status(200).send({ response: 'saved' })
} )
```

The request is transformed into JSON and placed into the ``req.body`` field, we extract the data and store it into our dictionary. For the hardware metrics we are going to do the same.

```js
let resources = {}


app.post('/resources', (req, res)  => {
  let data = req.body

  resources[data.pod] = data

  console.log('data ->', data)
  res.status(200).send({ response: 'saved' })
} )
```

Our service is ready to receive POST requests, but we need to add some way to retrieve the unified vision of all our pods.

```js
app.get('/resources', (req, res) => res.status(200).send(Object.values(resources)) )
app.get('/stats',     (req, res) => res.status(200).send(Object.values(stats)) )
```

This call is very similar to the one we used in our ``hello world`` we just return the values of our dictionary.

We do that because we are using the dictionary keys to quickly classify each pod, when somebody ask for a report we basically return an array with the values.

This is how we store it:

```js
{
  'x-1' : {
    {pod: 'x-1', value:'...'}
  },
  'x-2':{
    {pod: 'x-2', value:'...'}
  }
}
```

This what how we return it:

```js
[
  {pod: 'x-1', value:'...'},
  {pod: 'x-2', value:'...'}
]
```

### Running Our Service In OpenShift

First step, we need to configure our project to run using ``npm start``. We do this by adding a ``start`` entry to the ``package.json``:

```js
{
  "name": "mothership",
  "version": "1.0.0",
  "description": "",
  "main": "index.js",
  "scripts": {
    "test": "echo \"Error: no test specified\" && exit 1",
    "start": "node app.js"
  },
  "author": "",
  "license": "ISC",
  "dependencies": {
    "body-parser": "^1.18.3",
    "express": "^4.16.4"
  }
}
```

To run this service we just need to do:

```sh
npm start

> mothership@1.0.0 start /Users/cesar/Workspace/js/mothership
> node app.js

Listening: 8080!
```

#### Packaging

Preparing and packaging our service into a container can be done by creating a [build configuration](https://cesarvr.io/post/buildconfig/):

```sh
  oc new-build nodejs --binary=true --name=dashboard
```

Then we just run our build:

```sh
  oc start-build bc/dashboard --from-dir=. --follow

```

And get an image back:

```sh
  oc get imagestream

  #NAME        DOCKER REPO                       TAGS      UPDATED
  #dashboard   172.30.1.1:5000/hello/dashboard   latest    21 hours ago
```


#### Deploy

We can deploy this image creating a new deployment configuration:

```sh
oc create deploymentconfig dashboard --image=is/dashboard

#deploymentconfig "dashboard" created
```

#### ...And Expose
The last thing remaining then is to expose this service to external traffic:

```sh
oc expose dc/dashboard --port 8080
oc expose svc dashboard

oc get route

#NAME        HOST/PORT                             PATH      SERVICES    PORT
#dashboard   dashboard-hello.192.168.64.2.nip.io             dashboard   8080
```

Once we got the URL (``dashboard-hello.192.168.64.2.nip.io``) for our dashboard let's write some code in our decorator to post some statistics.

### Notifications

Our dashboard is deployed and waiting for our decorators container to start posting the state of applications running all over the cluster, but first we need to go back and add that capability in our *Decorator*.  

To post HTTP request we are going to install ``node-fetch`` using npm:

```sh
  npm install -S node-fetch
```

Let's create new class called *Notify*:

```js
class Notify {
  constructor ({ endpoint }) {
    this.URL = `${process.env['DASHBOARD']}/${endpoint}`
  }

  send({payload}) {
    if(this.URL !== '')
        return fetch(this.URL, {
          method: 'post',
          body:    JSON.stringify(payload),
          headers: { 'Content-Type': 'application/json' }
        })
        .then(res => res.json())
  }
}
```

This class reads the ``DASHBOARD`` URL from the environment variables which define the location of the dashboard and send a HTTP post request using the method ``send`` with a specify payload which can be any arbitrary object.

Usage example:

```js
  // https://dashboard.com/resource
  let notify = new Notify({ endpoint: 'resources' })

  notify.send({ pod:'hello-rwq3', data:'...' })
        .catch( err => console.log('endpoint not available') )
```

The method ``send`` returns a [Promise](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise) which is just an JavaScript object to encapsulate future actions i.e., server responses. If the *Dashboard* is not available our will fail gracefully and just show a message.


### Sending OS Resources

To post hardware resources to our dashboard we are going to write this simple timer:

```js
const TARGET = process.env['TARGET_PORT'] || 8087
/*...*/

let pod = new Pod()

setInterval(() => {
  let payload = {
    pod: pod.host(),
    resource: pod.resources
  }

  let notify = new Notify({ endpoint: 'resources' })

  notify.send({ payload })
        .catch( err => console.log('dashboard: resources endpoint not available') )
}, 1000)

function telemetry({service, server}) {/*...*/}
/*..*/
```

We just added a timer that each second executes a HTTP post request to the dashboard, with information about the CPU and memory usage.

### Service Metrics

For the service we are going to choose a lower frequency rate and we only post if there is new information is available.

```js
setInterval(() => {
  let payload = {
    pod: pod.host(),
    stats: db.all
  }

  console.log(`queue: ${db.size()}`)
  if(db.size() > 0) {
    let notify = new Notify({ endpoint: 'stats' })

    notify.send({ payload })
      .then(()   => db.clear() )
      .catch(err => console.log('dashboard: stats endpoint not available'))
  }
}, 5000)
```

Every five seconds we check the size of our *DB* object and see if there is something, if its true we report to the dashboard. If we get back a HTTP 200 from the dashboard, then we clear our array and start again.

#### Deploy

To deploy this changes we just reuse build upon the progress from last post, and reuse the build configuration we created before.

```sh
  oc start-build bc/decorator --from-dir=. --follow
```

If you remember in the last post we installed our decorated a Java service, so this service will get this update as a consequence of rebuilding this image. But it won't be able to target the dashboard because we need to provide the environment variable, so let's do that:

```sh
oc set env -c decorator dc/j-slow \
        TARGET_PORT=8080  \
        PORT=8087 \
        DASHBOARD=http://dashboard-hello.192.168.64.2.nip.io
```

Here we use ``oc set env`` command which set environment variables to the running pod, in our particular case our pod is running two containers (default, decorator). We need to setup the variables for the second container ``-c decorator``. The rest is just environment variable definition.

