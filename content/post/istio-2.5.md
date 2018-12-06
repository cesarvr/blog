---
title: "Creating Your Own Istio (Part 2.5)"
date: 2018-12-01
lastmod: 2018-12-01
draft: true
keywords: []
description: "Reusable Telemetry"
tags: [openshift, container, services, kubernetes ]
categories: [openshift, container, services, kubernetes ]
toc: true
image: https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
---

We just created our [first decorator container](https://cesarvr.io/post/istio-2/), The next step is to create a simple network profiler, taking this as an example we are going to learn how we can take advantage of the *man in the middle situation* of our container to gather some network information.

<!--more-->


### Reviewing The Code


Here is some code from the last post:

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

[This code](https://gist.github.com/cesarvr/d9fe6b6fdf8b8f3bba196654141507ef) just connects to any server running in ``TARGET_PORT`` and override their HTTP 404 responses with the content of the ``HTTP404`` string.

### Network Profiler
----------

#### Configuration

We can start by writing a new function to subscribe to the ``Ambassador::tunnel`` method.

```js
function telemetry({service, server}) {}

new Ambassador({port: PORT, target: TARGET})
      .tunnel({override_404, telemetry})
```

This function ``telemetry`` will get called each time a new HTTP request is being transmitted to the main container.

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

Let's create a class and register this object.

```js
class Stats {
  readRequest(header) {
    this.method   = header.HTTPMethod
    this.endpoint = header.HTTPResource

    return this
  }
}
```

The ``return this`` above is just to facilitate the chaining of calls, something like in the way of ``stats.a().b()``.

We instantiate the class and we provide the method, to the event listener:

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

Now let's register the responses from our target container.

```js
service.on('http:data', (header) => {})
```
We listen the ``service`` object for responses which generates a small HTTP response object:

```js
  {"status":"404","state":"File not found"}
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

#### Timing Responses

We are going to write two methods to handle the timing, one method will time the beginning of the service transaction (``startProfile``) and a second method time the response (``endProfile``).

Then we are going to calculate distance and we got our total time:

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

We need to call this two methods at the start of the request ``server`` and when the response is being delivered ``service``.

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

### Saving State

To make our *Stat* class useful we are going to persist its state by creating a *sophisticated* in-memory database.

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

This would be enough for now, we can focus now it gathering some more information and saving it in our in-memory database.

#### Resource Type

As you may notice our network profiler doesn't make distinction between URL resources, it doesn't distinguish between a file or a URL. A quick and dirty solution for this is to implement is a function to detect file extensions.

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

Then we add this to our in-memory database.

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

In case of problems we would like to know where this problem is originated, it can be important to cross this information with other factors, so let's register the pod name.

If you remember in first post we said that the pod simulates a machine, so we can know the pod name by just looking at the ``hostname`` which is simulated by the Linux [UTS Namespace](https://cesarvr.io/post/2018-05-22-create-containers/).

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

For this we are going to use Node.js ``os`` [hostname](https://millermedeiros.github.io/mdoc/examples/node_api/doc/os.html) API, we save this object in a field to avoid clutter the global namespace.

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

We know if it's a file, where is the *computation* is happening, the speed and the transaction type. But, now let's keep a record of this information, so if something goes wrong we can track its behavior through time.

Let's start by writing a new method called history:

```js
history(obj) {
  let history = obj.history || []

  return history
}
```

Basically it will read an arbitrary object will check for a field called ``history`` if not there create a new field with an **array**.

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

This will give us the following data structure:

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

We got the destination, the response and the time. But let's add a bonus by sampling container memory and CPU quota. You know, Linux can kill our container if we exceed memory constraint, with this feature we can keep track of the whole container memory state.

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

This new method give us this interesting information.

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

> Remember CPU usage time and memory is local to the container, meaning that it's constrained by [Linux control groups](http://cesarvr.io/post/2018-05-22-create-containers/#limiting-process-creation) to that particular pod.

Let add our time graph to our main object report.

```js
class Stats  {
  /*...*/
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

Now it's time to plug our new feature into the tunnel event bus, and we got ourselves a process capable of profiling any web service.

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

In the [last post](https://cesarvr.io/post/istio-2/#build-configuration) we created the build configuration to create our image, this time we just need to go back project folder and rebuild our image by using ``oc start-build`` command:


```sh
cd /project

oc start-build bc/decorator --from-dir=. --follow
```

And we should see our project running.

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2.5/profiler.gif)

This looks nice and all but is very difficult to make sense of that huge block, for that reason in the next post we are going to write a dashboard so we can make sense of our telemetry at real time.

Here is the code for this [telemetry probe](https://github.com/cesarvr/ambassador), if you find any optimization or improvement feel free to send a PR.
