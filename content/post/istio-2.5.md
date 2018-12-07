---
title: "Creating Your Own Istio (Part 2.5)"
date: 2018-12-01
lastmod: 2018-12-01
draft: false
keywords: []
description: "Reusable Telemetry"
tags: [openshift, container, services, kubernetes]
categories: [openshift, container, services, kubernetes]
toc: true
image: https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/static/logo/profiler.png
---

In the last post we create our first [container decorator](https://cesarvr.io/post/istio-2/), a container that when included into an arbitrary pod enhance the main container. In our particular case we created a container that override the HTTP 404 responses as an introduction, in this post we are going to build upon and develop some functionalities to monitor the performance of a running service.

<!--more-->

### Revisiting The Code

This is the code from the last post:

```js
let { Ambassador }  = require('../node-ambassador/')

const TARGET = process.env['target_port'] || 8087
const PORT   = process.env['port'] || 8080

const HTTP404 = `...`

function override_404({service, server}) {
  service.on('http:404', () => server.respond(HTTP404))
}

new Ambassador({port: PORT, target: TARGET})
      .tunnel({override_404})

console.log(`listening for request in ${PORT} and targeting ${TARGET}`)
```

[This code](https://gist.github.com/cesarvr/d9fe6b6fdf8b8f3bba196654141507ef) just connects to any server running in ``TARGET_PORT`` and override their HTTP 404 responses with the content from the ``HTTP404`` string. We are going to use this as our starting point.

### Network Profiler
----------

#### Configuration

We can start by writing a new function to subscribe to the ``Ambassador::tunnel`` method.

```js
function telemetry({service, server}) {}

new Ambassador({port: PORT, target: TARGET})
      .tunnel({override_404, telemetry})
```

The function ``telemetry`` will get called each time a new HTTP request is made by a HTTP client.

#### Request

The first functionality we want to write is the ability to register the HTTP request details, this will tell us what resources people or other services are looking in our web service.

```js
function telemetry({service, server}) {
    server.on('http:data',  (header) => {} )
}
```

We setup a listener for the event ``http:data`` in the *server* object and we receive a ``header`` object with two fields:

- **method** The HTTP Method ``GET, POST, DELETE, PUT,...``.

- **endpoint** The resource URL ``/Resource/1``.

Now we save the state into a class.

```js
class Stats {
  readRequest(header) {
    this.method   = header.HTTPMethod
    this.endpoint = header.HTTPResource

    return this
  }
}
```

We create a new class *Stats* and create the ``readRequest`` method taking saving the fields and returning ``this`` object. By returning ``this`` just make it easy for us to chain calls in the form of ``stats.a().b()``.

We instantiate the *Stats* class and bind the ``readRequest`` method to the event ``http:data``:

```js
class Stats {
  readRequest(header) {  /*...*/  }
}

let stats = new Stats()

function telemetry({service, server}) {
    server.on('http:data',  (header) => stats.readRequest(header) )
}
```

#### Tracking Responses

To capture responses, we need to listen for the ``http:data`` event but this time from the *service* object.

```js
service.on('http:data', (header) => {})
```
We listen the ``service`` object for responses which generates a HTTP response object with the following shape:

```js
  {"status":"404","message":"File not found"}
```

What we do now is save this data:

```js
class Stats  {
  readResponse(response) {
    this.response = response
    return this
  }
}  
```

We just need to *again* plug this method:

```js
class Stats {
  readRequest(header)    { /*...*/ }
  readResponse(response) { /*...*/ }
}

let stats = new Stats()

function telemetry({service, server}) {
  server.on('http:data',  (header) => stats.readRequest(header) )
  service.on('http:data', (header) => stats.readResponse(header) )
}
```

We have information about the request and responses. Next step is to calculate the time it takes for the target container to resolve a request.

#### Latency

We are going to write two methods to calculate how much it takes for our a service to respond, one method will time the beginning of the service request (``startProfile``) and a second method will time the response (``endProfile``).

Then we are going to calculate difference and we got our total time:

```xml
  latency = end_time - start_time
```

Let's implement this idea.

```js
class Stats  {

  //...
  startProfile(){
    this.start = new Date().getTime()
    return this
  }

  endProfile() {
    this.end =  new Date().getTime() - this.start
    return this
  }
  // ...
}
```

We plug this two methods one at the start of the request ``server->startProfile`` the other when the response is being delivered ``service->endProfile``.

```js
class Stats {
  readRequest(header) {    /*...*/ }
  readResponse(response) { /*...*/ }
  startProfile(){ /*...*/ }
  endProfile()  { /*...*/ }
}

let stats = new Stats()

function telemetry({service, server}) {
  server.on('http:data',  (header) => stats.readRequest(header)
                                           .startProfile())
  service.on('http:data', (header) => stats.readResponse(header)
                                           .endProfile())
}
```

We used the method chaining discussed before, this way we just subscribe once.


### Saving State

To make our *Stat* class useful we are going to persist its state by creating a nice *in-memory* database.

```js
class Stats {
  constructor(){
    this.db = {}
  }
}
```

To save the object state in memory we are going to write the method ``save`` and to retrieve the data the method ``all``.

```js
class Stats  {

  constructor(){
    this.db = {}
  }

  new(){
    let URL = this.endpoint
    this.db[URL] = this.db[URL] || {}

    this.db[URL] = { /* state */ }
  }

  get all(){
    return this.db
  }

  /*..*/
}
```

This would be enough for now for the db, let's focus now on gathering more information.

#### Resource Type

As you may notice our network profiler doesn't make distinction between a file or a URL. We can solve that by writing a function to detect file extensions.

```js

class Stats  {
/*...*/

isFile(endpoint) {
  const file_regexp = /\.[0-9a-z]+$/i
  return endpoint.search(file_regexp) !== -1
}

/*...*/
}
```

This is good enough for our purposes, let's persist this information.

```js
class Stats  {
/*...*/
  save(){
    let URL = this.endpoint
    this.db[URL] = this.db[URL] || {}

    this.db[URL] = { file: this.isFile(URL)  }
  }
/*...*/
}
```


#### Pod Name

In case of problems we would like to know where is happening, so it can be interesting to save the pod name.

> If you remember in first post we said that the pod simulates a machine, knowing this we can know the pod name by just looking at the ``hostname`` which is simulated by the Linux [UTS Namespace](https://cesarvr.io/post/2018-05-22-create-containers/).

```js
class Stats  {
  constructor(){
    this.os = require('os')
  }
  /*...*/
  host() {
    return this.os.hostname()
  }
  /*...*/
}
```

We use Node.js [os::hostname](https://millermedeiros.github.io/mdoc/examples/node_api/doc/os.html) API to get the hostname.

```js
class Stats  {
/*...*/
  save(){
    let URL = this.endpoint
    this.db[URL] = this.db[URL] || {}

    this.db[URL] = {
      file: this.isFile(URL),
      pod: this.host()
    }
  }
/*...*/
}
```

#### Registry

To simplify the diagnose of problems is smart to keep a track record, so we can correlate information and research for obscure runtime errors.

Let's start by writing a new method called history:

```js
history(obj) {
  let history = obj.history || []

  return history
}
```

This will read an arbitrary object and will check for a field called ``history`` if its not there, it create a new field with an **array**.

##### Timing

We save here the response latency, request and response. This will give us a picture of the transaction.

```js
history(obj) {
  let history = obj.history || []

  history.push({
    request: {endpoint: this.endpoint, method: this.method},
    response: this.response,
    time: this.end + 'ms',
    started: this.start
  })

  return history
}
```

This generates the following data structure:

```js
{
	"request": {
		"endpoint": "/",
		"method": "GET"
	},
	"response": {
		"status": "200",
		"state": "OK"
	},
	"time": "9ms",
	"started": 1544042305989
}
```

##### Container Resource

Another useful information we can extract from the pod is the memory and CPU usage. You know, Linux can kill our container if we exceed the memory constraints, this feature we can keep track of resources in the container.

We are going to create a new method called ``resources``:

```js
class Stats  {
  constructor(){
    this.os = require('os')
    /*...*/
  }
  /*...*/
  resources(){
    return {
      free_memory: this.os.freemem(),
      total_memory: this.os.totalmem(),
      cpus: this.os.cpus()
    }
  }
}
```

Again here we just use some [os](https://nodejs.org/api/os.html) functions to get the job done, I think this can be improve by studying the ``/proc`` directory.

```js
{
	/*...*/
	"resource": {
		"free_memory": 31891456,
		"total_memory": 8589934592,
		"cpu": "cpus": [{
				"model": "Intel Xeon...",
				"speed": 5300,
				"times": {
					"user": 153938390,
					"nice": 0,
					"sys": 73413290,
					"idle": 808839530
				}
			},
      /* More Cores... */
		}
	}
```

> CPU usage time and memory is local to the pod and shared between containers.

Let add our graph to our main report object.

```js
class Stats  {
  /*...*/
  resources(){ /*...*/}

  history(obj) {
    let history = obj.history || []

    history.push({
      request: {endpoint: this.endpoint, method: this.method},
      response: this.response,
      time: this.end + 'ms',
      started: this.start,
      resource: this.resources()
    })

    return history
  }

  new(){
    /*..*/
    this.db[URL] = {
      history: this.history(this.db[URL]),
      file: this.isFile(URL),
      pod: this.host()
    }
  }
  /*..*/
}
```

#### Reporting

Now it's time to plug our new feature into the ``tunnel`` event bus.

```js
class Stats {
  readRequest(header) {    /*...*/ }
  readResponse(response) { /*...*/ }
  startProfile(){ /*...*/ }
  endProfile()  { /*...*/ }
  save()        { /*...*/ }
  isFile(endpoint) { /*...*/}
  resources()  { /*...*/ }
  history(obj) { /*...*/ }
}

let stats = new Stats()

function telemetry({service, server}) {
  server.on('http:data',  (header) => stats.readRequest(header)
                                           .startProfile())

  service.on('http:data', (header) => stats.readResponse(header)
                                           .endProfile()
                                           .save())
}
```

To make this information available, let's create a 5 seconds refresh to show the data collected through standard output. In the next post we are going to replace this for HTTP calls.

```js
let stats = new Stats()

 setInterval(()=> {
   console.log('logs -> \n ', JSON.stringify(stats.all))
 }, 5000)

function handleConnection(server) {
/*

*/
}
```  
#### Deploy

To deploy our changes we can reuse the [build configuration](https://cesarvr.io/post/istio-2/#build-configuration) we have created before.

```sh
cd /project

oc start-build bc/decorator --from-dir=. --follow
```

And we should see our project running.

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2.5/profiler.gif)

This looks nice and all, but is very difficult to make sense of that huge block, for that reason in the next post we are going to write a dashboard so we can make sense of our telemetry at real time.

Here is the code for the [decorator container](https://github.com/cesarvr/ambassador), if you find any optimisation or improvement feel free to send a PR.
