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

[This code](https://gist.github.com/cesarvr/d9fe6b6fdf8b8f3bba196654141507ef) just connects to any server running in ``TARGET_PORT`` and override their HTTP 404 responses with the content of ``HTTP404`` string.

## Building Our Network Profiler

#### Tracking Request

First we need to track the URL, we want to register any new browser/HTTP client request to the *main container* to do this we are going to subscribe a new function to the *tunnel* method.

```js
function telemetry({service, server}) {}

new Ambassador({port: PORT, target: TARGET})
      .tunnel({override_404, telemetry})
```

This function ``telemetry`` will get called any time a new tunnel is established and will get two object as parameters, the *server* takes care of the request initiator I/O. We are interested in the *server*, so let subscribe to any new HTTP request using ``http:data`` event.

```js
function telemetry({service, server}) {
    server.on('http:data',  (header) => {} )
}
```
To read the HTTP request header we need to setup a listener for the event ``http:data`` in the *server* object.

When this event gets triggered, it pass a header object containing to fields:

- **method** The HTTP Method ``GET, POST, DELETE, PUT,...```.
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
  readRequest(header) {
    /*...*/
  }
}

let stats = new Stats()

function telemetry({service, server}) {
    server.on('http:data',  (header) => stats.readRequest(header) )
}
```

#### Tracking Responses

In this particular case we want to listen the event ``http:data`` in the *service* object, this event its triggered when the main container respond.


```js
service.on('http:data', (header) => {})
```
The **header** object has this shape:

```js
  {"status":"404","state":"File not found"}
```


Let's create a method to save that header in our *Stats* class.

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
  readRequest(header) {
    /*...*/
  }
  readResponse(response) {
   /*...*/
  }
}

let stats = new Stats()

function telemetry({service, server}) {
  server.on('http:data',  (header) => stats.readRequest(header) )
  service.on('http:data', (header) => stats.readResponse(header) )
}
```

#### Timing Responses

Any decent network profiler has the ability to time the request, we are going to write two methods to handle the timing, one method will handle the beginning of the service transaction (``startProfile``) and a second method taking a time sampling the end of the transaction (the service send a respond) (``endProfile``).

Then we are going to calculate the time distance:

```xml
  latency = response_time - delivering_time
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

We need to subscribe to two events one is triggered when the server is handling a request, in this case we are going to take advantage of the method chaining .

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

  }

  get all(){
    return this.db
  }

  /*..*/
}
```

#### Resource Type

As you may notice our network profiler doesn't make distinction between URL resources, it doesn't distinguish between a file or a URL, the solution for this is to implement is a function to detect file extensions, is a bit rudimentary but is a good start.

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

Knowing where the telemetry is coming from seems like a good idea, if you remember in first post we said that the pod simulates a machine, so we can know the pod name by just looking at the ``hostname`` which I bet is simulated by the Linux [UTS Namespace](https://cesarvr.io/post/2018-05-22-create-containers/).


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

Let's add this to our stats main object.

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

#### History

Well we know if its a file and who is doing the *compute*, but now let's collect some metrics, what we are going to do is to collect a history, this way we can keep track of the main container.

Let's start by writing a method called history:

```js
history(obj) {
  let history = obj.history || []

  return history
}
```

Basically it will read an arbitrary object and will make a new *array* field called *history*, if the field wasn't there before.

##### Timing

First thing we are going to save is the response timing, request and response. This will give us a picture of the transaction.

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

We got the destination, the response and the time. But let's add a bonus by sampling container memory and CPU quota just for fun. You know, Linux can kill our container if we exceed memory constraint, with this feature we can keep track of the whole container memory state  .

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

Now we plug into our main report and we get a very interesting picture of the state of pod, services, business logic, etc. Making our framework very competitive in the "Service Mesh" market.

```js
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
```
### Deploying


Now it's time to plug our new feature into the tunnel event bus, and we got ourselves a process capable of profiling any web service.

```js
class Stats {
  readRequest(header) {    /*...*/ }
  readResponse(response) { /*...*/ }
  startProfile(){ /*...*/ }
  endProfile()  { /*...*/ }
  save()        { /*...*/ }
  isFile(endpoint) { /*...*/}
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

If we execute this script and target at our Python server we deployed in the last post we are going to see something like this:
