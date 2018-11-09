---
title: "Creating Your Own Istio (Part 2)"
date: 2018-11-07
lastmod: 2018-11-07
draft: false
keywords: []
description: "Creating our reusable container."
tags: [openshift, container, services, kubernetes ]
categories: [openshift, container, services, kubernetes ]
toc: true
image: https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
---

Last post we learn how the pod simulates a logical host (machine), how we can run multiple containers inside and how they share the same network IP address. Now in this post we are going take advantage of this to add functionality to new or existing services running in Kubernetes/OpenShift.

First of all we are going to create a set of nice features, then we are going to explore how we can make those features reusable across services talking our same language.    

Let's start by defining our service features:  

- How many time a HTTP resource is being requested.
- Handle 404 Page.
- How fast is this resource being served.

# Let's Write Some Code

## Server

We can start by creating a HTTP server, to do this we are going to use a raw [Posix/Socket](http://man7.org/linux/man-pages/man2/socket.2.html).

```js
var net = require('net')

console.log('Listening for request in 8080')
net.createServer( function (socket) {
  console.log('new connection!')
  socket.end()
}).listen(8080)
```

Here we require the [net](https://nodejs.org/api/net.html) which has all the libraries we need to manipulate sockets, then we start listening in port 8080 for incoming request, we got an incoming request we close the port and finish. Why a raw socket? Because we want to keep the main HTTP request as raw and untouched as possible, you will see why later.

We are going to name this file as ```sitio.js``` and run this script with:

```sh
node sitio.js
# Listening for request in 8080
```

Calling in our browser will give us this response:

![](https://github.com/cesarvr/hugo-blog/blob/master/static/istio-2/empty-response.png?raw=true)

Notice that it say *empty response* this mean that we are connecting but doing nothing.

## Input/Output

We are going to start by taking the socket out to its own function.

```js
var net = require('net')


function handle(socket) {
 // handle the socket
}

console.log('Listening for request in 8080')
net.createServer( function (socket) {
  console.log('new connection!')
  handle(socket)
}).listen(8080)
```

Let's make a class to handle all the details about our incoming traffic.

```js
class IncomingTraffic {
  constructor({socket}) {
    this.socket = socket
    this.socket.on('data', data => console.log(data))
  }
}
```
We create a simple class that takes the socket subscribe to the socket data events, this mean every time new data is available in the socket that anonymous function get triggered.  

```js
function handle(socket) {
  this.incomingTraffic = new IncomingTraffic({socket})
}
```

The idea is to have only one place to handle this (IncomingTraffic object). As you might know Node.js uses an asynchronous I/O which is a bit difficult to handle using classic OOP paradigm, for this reason let's make our object capable of emitting events. This way we can easily connect the objects to get what we want.

```js
class IncomingTraffic extends Events {
  constructor({socket}) {
    super()
    this.buffer = null
    this.socket = socket
    this.socket.on('data', data => this.emit('traffic:incoming', data))
  }
}
```

Ok, now our class will control the data flow in behalf of the socket, let's write a method to send data to the socket.

```js
class IncomingTraffic extends Events {
  constructor({socket}) {
    super()
    this.buffer = null
    this.socket = socket
    this.socket.on('data', data => this.emit('traffic:incoming', data))
  }

  send(chucks){
    chucks.forEach(data => this.socket.write(data) )
    this.socket.end() //close socket connection
  }
}
```

Sometimes, the data we want to transfer is to big and can break the socket limit and close the connection unexpectedly. This is why our *send* method will take an array and will feed the socket one chunk at a time, then close the connection.

## Custom 404

After all this code we are still in the same place, but no worries, we are going to demonstrate the use of *IncomingTraffic* class to create our HTTP 404 response. We are going to show this page when the page or resource we are looking for doesn't exist.

First let's define our 404 page:

```js
const HTTP404 = `
HTTP/1.0 404 File not found
Server: Sitio 💥
Date: ${Date}
Content-Type: text/html
Connection: close

<body>
  <H1>Endpoint Not Found</H1>
  <img src="https://www.wykop.pl/cdn/c3201142/comment_E6icBQJrg2RCWMVsTm4mA3XdC9yQKIjM.gif">
</body>`
```

For simplicity here we are using a constant and we using JavaScript [string interpolation](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals) to add some info. We can safely assume that our service doesn't have nothing to show yet so we can just code the response like this. 


```js
  function handle(socket) {
    let traffic = new IncomingTraffic({socket})

    traffic.on('traffic:incoming', incomingTraffic => traffic.send([HTTP404]) )
  }
``` 

Here we are saying, if we got some incoming request just send back the 404 page. 


## Parsing HTTP

Now that we setup our class *Stats*, let's add some HTTP parsing capabilities.

```js
class Stats {
  constructor({socket}) {
    socket.on('data', data => this.read(data))
  }

  getResource(http_block) {
    let str = http_block.split('\n')[0]

    return str.replace("GET", "")
      .replace("HTTP\/1.1","")
      .trim()
  }

  read(data){
    let str_data = data.toString()
    let endpoint = this.getResource(str_data)
  }
}
```

We added the method *getResource* which takes some raw [HTTP request header](https://developer.mozilla.org/en-US/docs/Glossary/Request_header) and extract the endpoint URL. It basically takes this header ```GET /hello HTTP/1.1 ``` and get this URL ```/hello```.

## In-Memory Cache

We got our URL, next step is to persist the URL somewhere. To make it simple let's create a class to handle that particular behaviour.

```js
class Store {
  constructor() {
    this.db = {}
  }

  save(value) {
    this.db[value.endpoint]      =  this.db[value.endpoint] || {}
    this.db[value.endpoint].hit  =  this.db[value.endpoint].hit || 0
    this.db[value.endpoint].hit +=1
  }

  get all(){
    return this.db
  }
}
```

This very rudimentary in-memory store will do the persistence for us, any time an endpoint URL gets repeated we just add one to the *hit* counter.

We put all together:

```js
var net = require('net')

class Store {
  constructor() {
    this.db = {}
  }

  save(value) {
    this.db[value.endpoint]      = this.db[value.endpoint] || {}
    this.db[value.endpoint].hit  = this.db[value.endpoint].hit || 0
    this.db[value.endpoint].hit += 1
  }

  get all(){
    return this.db
  }
}

class Stats {
  constructor({socket, store}) {
    socket.on('data', data => this.read(data))
  }

  getEndPoint(http_block) {
    let str = http_block.split('\n')[0]

    return str.replace('GET', '')
      .replace('HTTP\/1.1','')
      .trim()
  }

  read(data){
    let str_data = data.toString()
    let endpoint = this.getEndPoint(str_data)

    store.save({endpoint})
  }
}

let store = new Store()

// We added this for now to get an update on the stats every 5 seconds.
setInterval(() =>
  console.log('endpoint->', store.all),
  5000)

function handle(socket) {
  let stats = new Stats({socket})
}

console.log('Listening for request in 8080!!')
net.createServer( function (socket) {
  console.log('new connection!')
  handle(socket)
}).listen(8080)

```

When we run our application again, we can see now we are able to tell what resources the browser is trying to get access to:

```
node sitio.js

#Listening for request in 8080!!
#endpoint:  { '/': 1 }
#new connection!
#endpoint:  { '/': 2 }
#new connection!
#endpoint:  { '/': 3 }
#new connection!
#endpoint:  { '/': 3, '/my_service': 1 }
#new connection!
#endpoint:  { '/': 3, '/my_service': 2 }
```

## Custom 404

Other thing we wanted to do is to show our own page, any time we can found a resource in our service. We are going to encapsulate this behaviour in its own class.

```js

const HTTP404 = `
HTTP/1.0 404 File not found
Server: Sitio 💥
Date: Thu, 08 Nov 2018 12:25:33 GMT
Content-Type: text/html
Connection: close

<body>
  <H1>Endpoint Not Found</H1>
  <img src="https://www.wykop.pl/cdn/c3201142/comment_E6icBQJrg2RCWMVsTm4mA3XdC9yQKIjM.gif">
</body>`

class Traffic {
  constructor({socket}) {
    socket.write(HTTP404)
    socket.end()
  }
}
```
For simplicity we define our HTML in a constant, at the moment every call to our service will show this page. We call this class inside our handle function and we are good to go.  


```js

function handle(socket) {
  let stats = new Stats({socket})
  let traffic = new Traffic({socket})
}

```

![](https://github.com/cesarvr/hugo-blog/blob/master/static/istio-2/traffic_stats.gif?raw=true)

# Reusing Features

Let's first build a service, just to have something that we can enhance we new functionality. To make sure we don't cheat let make this service in other programming language or even better let's do it in a way we cannot touch the source code.

For this web server we are going to use Python SimpleHTTPServer module which can be use to serve the content of a folder:

![python server](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/python-server.gif)  

You can serve any folder using this command:

```sh
  python -m SimpleHTTPServer 8087
```
Great what we are going to do is to transform our application into some kind of Proxy, but in reality we just going to handle the request do our stuff and then delegate the request to the service.

Let's write some code to do this, let's start by making a connection with our image service:

```js
let delegate = function(port){
  let client = new net.Socket()
  client.connect(port || 8087, '0.0.0.0', function() {
    console.log(`connected to ${port}`)
  })
  return client
}
```
This function will create a connection to localhost port 8087 and will return the socket. Next step, is to stream the content from the incoming traffic to this newly created socket.

Every time a browser opens a new connection, we need to make contact with the service:

```js
function handle(socket) {
  let client = delegate(8087)
  socket.on('data', read)
}
```

When the contact has been established, we want our service to do its thing and then just proxy the HTTP payload to its real target(the service).

```js

function read(data) {
  let str_data = data.toString()
  let endpoint = extractURL(str_data)
  track.save(endpoint)
  console.log('endpoint: ', track.all() )
  return data
}

function handle(socket) {
  let client = delegate(8087)
  socket.on('data', data => client.write(read(data)))
}
```

In the ```read``` function we added a return routine, so this function return the HTTP payload, then tunel the incoming traffic. When the request hit the service we need to handle the response back.

```js
function handle(socket) {
  let client = delegate(8087)

  socket.on('data', data => client.write(read(data)))
  client.on('data', data => socket.write(data))
}
```
The only thing left is to free up the resources, for that we just going to wait for a 'end/close' signal from the socket and we disposse all the resources.

```js
function handle(socket) {

  let client = delegate(8087)

  socket.on('data', data => client.write(read(data)))
  client.on('data', data => socket.write(data))
  socket.on('end', end => client.end())
  socket.on('close', end => client.end())
}
```
