---
title: "Creating Your Own Istio (Part 2.5)"
date: 2018-11-07
lastmod: 2018-11-07
draft: true
keywords: []
description: "Reusable Telemetry"
tags: [openshift, container, services, kubernetes ]
categories: [openshift, container, services, kubernetes ]
toc: true
image: https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
---

We are going to create a reusable telemetry container, to do this we are going to build upon our last project. The strategy we are going to follow to make our network profiler, is to take advantage of our man in the middle situation to get measure the latency, detect errors, report on service status, payload size, etc.  

#### Tracking Request

To make our profiler we first need to know what URL resource the client is trying to access, to get this information we are can subscribe to an event provided by the *HTTPServer* class called *[server:http:headers](https://www.npmjs.com/package/node-ambassador#events-1)*, this event gets trigger any time a HTTP header is detected, giving us the following header object:

```js
{
  HTTPMethod,   //HTTP Method   -> GET
  HTTPResource  //HTTP Resource -> /home
}
```

We just need to create a class called *Stats*, with the method ``readRequest`` to read  the state of the HTTP request header.

```js
class Stats  {

  readRequest(header){
    this.method   = header.HTTPMethod
    this.endpoint = header.HTTPResource

    return this
  }
}
```

We subscribe this method to the *[server:http:headers](https://www.npmjs.com/package/node-ambassador#events-1)* event.

```js

function handleConnection(server) {
  /*...*/
  server.on('server:http:headers',   
                          (header, data) => stats.readRequest(header) )
  /*...*/
}
```

And to persist the state we are going to initialise our new *Stat* object outside of the scope of the function.

```js
// bounded to the application life cycle.
let stats = new Stats()


function handleConnection(server) {
  /*...*/
  let service = new HTTPService({port: tport })

  server.on('server:http:headers',   
                          (header, data) => stats.readRequest(header) )
  /*...*/
}
```

This should be enough to register any HTTP request.

#### Tracking Responses

Another thing of interest is what response we got from the service, we can track this value first by creating a method.

```js
class Stats  {
  readResponse(response) {
    this.response = response
    return this
  }
}  

```

We just need to plug this method to the *HTTPServer* ``service:http:header`` event, and saving the header object which contains the HTTP response headers.

```js
// bounded to the application life cycle.
let stats = new Stats()


function handleConnection(server) {
  /*...*/
  server.on('server:http:headers',   
                          (header, data) => stats.readRequest(header) )

  service.on('service:http:headers', (header, data) =>
                                            stats.readResponse(header) )
  /*...*/
}
```

The header object has this shape:

```js
  {"status":"404","state":"File not found"}
```


#### Timing

Any decent network profiler has the ability to time the request, we are going to write two methods to handle the timing, one method will handle the beginning of the service transaction (``startProfile``) and a second method taking a time sampling the end of the transaction (the service send a respond) (``endProfile``).

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

We need to subscribe to two events one is triggered when the server is handling a request.

```js
let stats = new Stats()


function handleConnection(server) {
  /*...*/
  server.on('server:http:headers',   
                          (header, data) => stats.readrequest(header)
                                                 .start_profile() )

}
```

An other event for the response.

```js

function handleConnection(server) {
  /*...*/
  server.on('server:http:headers',   
                          (header, data) => stats
                                            .readRequest(header)
                                            .startProfile() )

  service.on('service:http:headers',
                          (header, data) => stats
                                            .readResponse(header)
                                            .endProfile() )
}
/*....*/
```

> The reason we are able to chain calls in the form of ``stats.a().b()`` is because we are returning ``this`` an instance of the class, in all methods.

### Tracking Resource Type

Another interesting metric we can collect is if the URL we are trying to access belong to a file, this way we can create a filter to separate asset request from endpoints.

```js
  isFile(endpoint) {
    const file_regexp = /([a-zA-Z0-9\s_\\.\-\(\):])+(.jpg|.doc|.pdf|.zip|.docx|.pdf|.gif|.png|.ico)$/

    return endpoint.search(file_regexp) !== -1
  }
```

The algorithm is very simple, just check if the URL have an file extension.

```xml
/home -> false

/home.pdf -> true
```



### Saving State

To make our *Stat* class useful we are going to persist its state by create a in-memory database using a JavaScript object.

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

  new_entry(){
    let URL = this.endpoint
    this.db[URL] = this.db[URL] || {}

    this.db[URL] = {
                    started: this.start,  
                    time: this.end + 'ms',
                    response: this.response,
                    file: this.isFile(URL)
    }
  }

  get all(){
    return this.db
  }

  /*..*/
}
```

We save the object state just after we receive the response to the TCP client.

```js

function handleConnection(server) {
  /*...*/

  service.on('service:http:headers',
                          (header, data) => stats
                                            .readResponse(header)
                                            .endProfile()
                                            .new() )
}
/*....*/
```

To make this information available, let's create a 5 seconds refresh to show the data collected through standard output. In the next post we are going to replace this with a HTTP call to a centralize server.

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

After we run our proxy we try to call some URL and after 5 seconds we start getting the usage data:

```json
{
    "/": {
        "file": false,
        "response": {
            "state": "ok",
            "status": "200"
        },
        "started": 1542964406354,
        "time": "1ms"
    },
    "/as07-3-1531_21921290751_o.jpg": {
        "file": true,
        "response": {
            "state": "ok",
            "status": "200"
        },
        "started": 1542964403179,
        "time": "1ms"
    },
    "/favicon.ico": {
        "file": true,
        "response": {
            "state": "file not found",
            "status": "404"
        },
        "started": 1542964406416,
        "time": "2ms"
    }
}
```

We are getting this information by being the middleware of a local Python server, the next step is to pack this process into its own container and share this functionalities with any application running in Kubernetes/OpenShift.
