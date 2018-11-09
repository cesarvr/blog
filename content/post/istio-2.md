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

![HTTP 404](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/404.png)


## Usage Patterns 

Now our service is able to return a 404 page, but let make it a bit more interesting add a supervisor that checks and save the usage patterns of our service.  

Let's start by encapsulating this new behaviour in a class. 

```js
class Stats  {

  read(httpHeader){
    let head = httpHeader.toString()
  }
}

```

This class will have a *read* method, that will take a HTTP header in the form of a [Buffer](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=1&cad=rja&uact=8&ved=2ahUKEwjSxv6_q8feAhWSPFAKHX_lBwIQFjAAegQIBhAB&url=https%3A%2F%2Fnodejs.org%2Fapi%2Fbuffer.html&usg=AOvVaw1jQcAyZipqNZ410cf4j8HS). The Buffer object is just a Node.js abstraction to save binary data, we use the method *toString* to transform it into *utf-8* string.  

### Parsing The HTTP Header

We we transform the buffer into a string we are going to get something like this: 

```sh
 GET /user HTTP/1.1
 Host: 0.0.0.0:8080
 User-Agent: curl/7.54.0
```

To keep it simple we just want to keep track how many call we receive per endpoint. To do this we just parse this block to retrieve the destination URL ``  /user ``.   

```js
class Stats  {
  getEndPoint(http_block) {
    let str = http_block.split('\n')[0]

    return str.replace("GET", "")
      .replace("HTTP\/1.1","")
      .trim()
  }

  read(httpHeader){
    let head = httpHeader.toString()
    let endpoint = this.getEndPoint(head)
  }
}
```
The method ``getEndpoint`` removes the HTTP Verb and the HTTP version and give us back the URL. Now let's create some way to persist this information and add some mechanism to keep the count of how many time our endpoint get visited.

```js
class Stats  {

  constructor(){
    this.db = {}
  }

  //getEndPoint(http_block) ... 

  save(value){
    this.db[value.endpoint]      =  this.db[value.endpoint] || {}
    this.db[value.endpoint].hit  =  this.db[value.endpoint].hit || 0
    this.db[value.endpoint].hit += 1
  }

  read(httpHeader){
    let head = httpHeader.toString()
    let endpoint = this.getEndPoint(head)

    this.save({endpoint})
  }

  get all() {
    return this.db
  }
}
```

Our "*sophisticated quick and dirty in-memory data store*" does just that. We just make a dictionary to save all the entries and to keep the counting using the *hit* property. Next we are going to instantiate the *Stat* class to make it persistent through the live cycle of the application, also we are going to take the liberty to report every 2 seconds to the [stdout](http://www.linfo.org/standard_output.html).  

```sh 
let stats = new Stats()

setInterval(() =>
  console.log('endpoint->', stats.all),
  2000)

function handle(socket) {
  let traffic = new IncomingTraffic({socket})

  traffic.on('traffic:incoming', incomingData => stats.read(incomingData))
  traffic.on('traffic:incoming', incomingTraffic => traffic.send([HTTP404]) )
}

```

If we re-execute our script we get something like this:

![Traffic and Statistics](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/traffic_stats.gif)


# Decorating Other Services 

## Web Server

If you remember the key of all this is to learn how to re-use functionality across micro-services, before we start we need a service, so let's start by making a simple web server. 

To make thing more interesting we are going to use Python [SimpleHTTPServer](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=1&cad=rja&uact=8&ved=2ahUKEwjZt_6tscfeAhWSaFAKHc8NBawQFjAAegQIBBAB&url=https%3A%2F%2Fdocs.python.org%2F2%2Flibrary%2Fsimplehttpserver.html&usg=AOvVaw3mE6UK_OSre6HPTQoN3mIF) module. We are going to choose this because we don't have control over the source code and because the only thing we have in common is the we talk the same protocol *HTTP*.  
 
A have some folder in a folder so I'll create some sort of HTTP photo library. 

```sh
cd /my_photo_folder

# Python 2.xx
python SimpleHTTPServer 8087

# Python 3.xx
python -m simple.http 8087
```

![Python server](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/python-server.gif)


## Communicating With Other services

This web server looks good, but we want to know what pictures are more popular and also if our users make a mistake they will be redirected to a generic 404. Let's write some code to transfer apply this new features. The first step is to create a connection with this new service.

We can start by revisiting our `` sitio.js`` and create a new class called *Service*. 

```js
class Service {
  constructor(_port) {
    let port = _port || 8087
    let client = new net.Socket()

    client.connect(port, '0.0.0.0', () => {
      console.log(`connected to ${port}`)
    })
  }
}

```

This class handles the creation of a new socket, but this time, the socket is opening communication with a port inside our logical host (0.0.0.0). Do you remember that pods simulate a machine? We are going to use this fact later to connect to any container running in our same neighborhood. 


Next thing we need to implement is how we send/receive information from that socket. 

```js 

class Service {
  constructor(_port) {

    let port = _port || 8087
    let client = new net.Socket()

    client.connect(port, '0.0.0.0', () => {
      console.log(`connected to ${port}`)
    })

    client.on('data', data => this.read(data))
    client.on('end', data  => this.finish(data))
    client.on('error', err  => console.log('err->', err))

    this.client = client
    this.buffer = []
  }

  send(data) {
    this.client.write(data)
  }

  read(data){
    this.buffer.push(data)
  }

  finish(){
    // The service has finished... do something.
  }
}
``` 

The plan here is simple, we implemented a *send* method to send any type of data to the service, then the response is handled by the method *read* which gets call when the remote service sends some data back. To enhance our compatibility we are handling responses coming in chunks, of course if some service is streaming 1GB back we are in trouble, but for demo purposes is good enough. 

They are two things remaining we want to override that ugly HTTP 404 response, to do that we need to write some code that detects when something like that happens in the service so we are able to replace that page with our page.  

Our service will respond something like this:  

```
HTTP/1.0 404 File not found
```

We just need to read the second parameter separated by space from left to right, to do just that we are going to write a helper function. 

```js
let HTTP = Object.create({
  getStatus: function(data){
    let headerFirstLine = data.toString().split('\n')[0]
    let status = headerFirstLine.split(' ')[1].trim()
    return status
  }
})

class Service {
  constructor(_port) {
    //...stuff
  }

  // We cache everything in buffer

  finish(){
    let status = HTTP.getStatus(this.buffer[0])
  }
}
```

Here we pass the first data chuck which contain the HTTP response header and we get back the status.


The second thing missing here is that we should look for a way to communicate all this to other components of the application. For this again, we are going to make this object inherit from Events. 

```js
class Service extends Events {
  constructor(_port) {
    super()
    // Initialization...
  }

  finish(){
    let status = HTTP.getStatus(this.buffer[0])
    this.emit(`service:response:${status}`, this.buffer)
  }
}
```
The important part here is the usage of ``this.emit``. We are going to create a new event of the form ``service:response:`` and we going to append the status at then end. This will give us the flexibility to append behaviour to each case as we see fit.   


```js
class Service extends Events {
  constructor(_port) {
    super()
    // Initialization...
  }

  finish(){
    let status = HTTP.getStatus(this.buffer[0])
    this.emit(`service:response:${status}`, this.buffer)
  }
}

function handle(socket) {
  let service = new Service()
  let traffic = new IncomingTraffic({socket})

  traffic.on('traffic:incoming', incomingData => stats.read(incomingData))
  traffic.on('traffic:incoming', incomingData => service.send(incomingData))

  service.on('service:response:200', response => traffic.send(response) )
  service.on('service:response:404', response => traffic.send([HTTP404]) )
}
```

Any time we got a 404 we send our page and if we got a 200 we just return the service response. I saw a demo of Istio where they show how the framework mask HTTP 500 by sending a previously cached response. How you will implement that ?.   







 

