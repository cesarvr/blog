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

[In the last post](https://cesarvr.io/post/istio/) we learn how the pod simulates a logical host (AKA machine), how we can create pod composed of multiple containers, and how we they can co-operated together.

In this post we are going to create a special type of Proxy with its own domain of expertise, and we are going to share this knowledge with any service in the cluster as long as it support the HTTP protocol.

Let's start by defining features we want to share with other service:  

- How many time a HTTP resource is being requested.
- Handle 404 Page.
- How fast is this resource being served.

# Writing Some Code

## Server

To write our "Proxy" container using JavaScript/Node.js, we can start by creating a TCP server using a raw [Posix/Socket](http://man7.org/linux/man-pages/man2/socket.2.html).

```js
var net = require('net')

console.log('Listening for request in 8080')
net.createServer( function (socket) {
  console.log('new connection!')
  socket.end()
}).listen(8080)
```

Here we require the [net](https://nodejs.org/api/net.html) library which has the socket API, then we create a new TCP server listening in port 8080 for incoming request. When a new client connects to our server we just do nothing and close the port.

We are going to name this file as ```sitio.js``` and run it:

```sh
node sitio.js
# Listening for request in 8080
```

Calling in our browser will give us this response:

![](https://github.com/cesarvr/hugo-blog/blob/master/static/istio-2/empty-response.png?raw=true)


## Input/Output

When a new client (like a browser) connects to our server, this function generates a new socket. To make things easy to understand we are going to handle this socket, in a function.

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

We need to write some code to handle the input/output of data through that socket, so let's handle those behaviours in a class.


```js
class IncomingTraffic {
  constructor({socket}) {
    this.socket = socket

  }
}
```

Node.js make heavy use of events to handle I/O, so we need to subscribe when the data is coming our way.

```js
class IncomingTraffic {
  constructor({socket}) {
    this.socket = socket
    this.socket.on('data', data => console.log(data))
  }
}
```

This solves the read at the moment, let's take care of defining a write method.

```js
class IncomingTraffic {
  constructor({socket}) {
    this.buffer = null
    this.socket = socket
    this.socket.on('data', data => console.log(data))
  }

  send(chucks){
    chucks.forEach(data => this.socket.write(data) )
    this.socket.end() //close socket connection
  }
}
```

We just write a *send* method that will take an array and will feed the socket one chunk at a time and close the connection.

We need to make other objects aware of the data coming to the socket, but at the same time we want to keep this object from knowing to much. So, we are going to share this information by emitting events.


```js
class IncomingTraffic extends Events {
  constructor({socket}) {
    super()
    this.buffer = null
    this.socket = socket
    this.socket.on('data', data => this.emit('traffic:new', data))
  }

  send(chucks){
    chucks.forEach(data => this.socket.write(data) )
    this.socket.end() //close socket connection
  }
}
```


## Custom 404

After all this code we are still in the same place, but no worries, we are going to demonstrate the use of *IncomingTraffic* class to create our HTTP 404 response. We are going to show this page when the resource we are looking for doesn't exist.

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

For simplicity here we are using a constant and we using JavaScript [string interpolation](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals) to add some info.


To implement our 404 web page, we need to implement our class to handle the input/output flow.

```js
  function handle(socket) {
    let traffic = new IncomingTraffic({socket})
  }
```

We subscribe to the ``traffic:new`` event.  

```js
  function handle(socket) {
    let traffic = new IncomingTraffic({socket})
    traffic.on('traffic:new', incomingTraffic => traffic.send([HTTP404]) )
  }
```

Here we are saying, if we got some incoming request just send back the 404 page.

![HTTP 404](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/404.png)


## Usage Patterns

Now our service is able to return a 404 page, but let make it a bit more interesting by adding usage tracking.  

Let's start by encapsulating this new behaviour in a class.

```js
class Stats  {

  read(httpHeader){
    let head = httpHeader.toString()
  }
}

```

This class will have a *read* method, that will take a HTTP header in the form of a [Buffer](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=1&cad=rja&uact=8&ved=2ahUKEwjSxv6_q8feAhWSPFAKHX_lBwIQFjAAegQIBhAB&url=https%3A%2F%2Fnodejs.org%2Fapi%2Fbuffer.html&usg=AOvVaw1jQcAyZipqNZ410cf4j8HS). The Buffer object is just a Node.js abstraction to save binary data, we use the method *toString* to transform it to an *UTF-8* string.  

### Parsing The HTTP Header

When we transform the buffer into a string we are going to get something like this:

```sh
 GET /user HTTP/1.1
 Host: 0.0.0.0:8080
 User-Agent: curl/7.54.0
```

To keep it simple we just want to keep track how many calls we receive per endpoint.

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
The method ``getEndpoint`` removes the HTTP Verb and the HTTP version and give us back the URL.


Now let's persist this information and add a visit counter.

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

 We just make a dictionary to save all the entries and we keep the counting by using the *hit* property. Next we are going to instantiate the *Stat* class to make it persistent through the application lifecycle.

```js
let stats = new Stats()

function handle(socket) {
  let traffic = new IncomingTraffic({socket})

  traffic.on('traffic:new', incomingData => stats.read(incomingData))
  traffic.on('traffic:new', incomingTraffic => traffic.send([HTTP404]) )
}
```

We add some code to shows the tracking information every two seconds.

```js
setInterval(() =>
  console.log('endpoint->', stats.all),
  2000)

  function handle(socket) {
    let traffic = new IncomingTraffic({socket})

    traffic.on('traffic:new', incomingData => stats.read(incomingData))
    traffic.on('traffic:new', incomingTraffic => traffic.send([HTTP404]) )
  }
```

We run our script:

![Traffic and Statistics](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/traffic_stats.gif)


# Proxy

## Design

Right now our "Proxy" looks something like this:

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/404-stats.png).

Our browser start communication in *port 8080*, we receive the data, gather some usage statistics and return the 404 page.

To make this usage statistics and the 404 page more interesting we need to write some code, that tunnel the request without loosing this functionality.

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/full-proxy.png)


We want to handle the traffic coming from the browser, apply some logic and then delegate the request to its real destination.


## Implementation

The *Service* class will handle the communication with the processes running inside the pod.

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

The communication is established again using a [TCP Socket](http://man7.org/linux/man-pages/man2/socket.2.html), but this time, we are connecting to ``localhost`` port *8087*. We choose this port arbitrarily, we just need to match the port of the running service.


### Read/Write

To handle the communication we are going to create again two methods:

```js

class Service {
  constructor(_port) {

    let port = _port || 8087
    let client = new net.Socket()

    client.connect(port, '0.0.0.0', () => {
      console.log(`connected to ${port}`)
    })
  }

  send(data) {
    this.client.write(data)
  }
}
```

Method *send*:  For sending data to the deployed micro-service.

```js
class Service {
  constructor(_port) {
    super()

    let port = _port || 8087
    let client = new net.Socket()

    client.connect(port, '0.0.0.0', () => {
      console.log(`connected to ${port}`)
    })

    client.on('data', data => this.read(data))
    this.buffer = []
  }

  send(data) {
    this.client.write(data)
  }
  read(data){
    this.buffer.push(data)
  }
}
```

Method *read*: To read the response, coming from the service. We also subscribe the read method, to Node.js ``data`` event.  

### Multi-Chunk Support

To make our "Proxy" more robust we are going to add support for emission of data with multiple chunks. The key to do this is to wait until the micro-service sends a close packet. When Node.js see this packet it emit a ``end`` event.  

```js
class Service {
  constructor(_port) {
    // ...
    // ...
    client.on('end', ()  => this.finish())
    this.buffer = []
  }

  // ...

  finish(){
    // We got all the information
  }
}
```

Of course this implementation is holding everything in memory, which make it vulnerable to huge responses. But for our demo purposes will be fine.

### Event Driven

As we did with *IncomingTraffic*, we are going to delegate what to do with this flow of data to more specialised classes by extending from Events.

```js
class Service extends Events {
  constructor(_port) {
    // ...
    client.on('end', ()  => this.finish())
    this.buffer = []
  }

  // ...
  finish(){
    this.emit('service:response:200', this.buffer)
  }
}
```

We implement this class like this:

```js
function handle(socket) {
  let service = new Service()
  let traffic = new IncomingTraffic({socket})

  traffic.on('traffic:new', incomingData => stats.read(incomingData))
}
```

The *Service* class hides all the complexity of connecting with the micro-service by giving us a set of interfaces.

To tunnel the data from the browser to the micro-service we use this:

```js
traffic.on('traffic:incoming', incomingData => service.send(incomingData))
```

To tunnel the response from the micro-service to the browser:


```js
service.on('service:response:200', response => traffic.send(response) )
```

![]()


## Overriding Responses

We want to give some personality to our service in the cluster, by sharing our custom HTTP 404 response.

We need to read the HTTP response of

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

## Handling Service State

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




## Web Server

To make thing more interesting we are going create a *web server* using Python [SimpleHTTPServer](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=1&cad=rja&uact=8&ved=2ahUKEwjZt_6tscfeAhWSaFAKHc8NBawQFjAAegQIBBAB&url=https%3A%2F%2Fdocs.python.org%2F2%2Flibrary%2Fsimplehttpserver.html&usg=AOvVaw3mE6UK_OSre6HPTQoN3mIF) module. This will create a server that we can enhance later.

Let's create some sort of HTTP photo library.

```sh
cd /my_photo_folder

# Python 2.xx
python SimpleHTTPServer 8087

# Python 3.xx
python -m simple.http 8087
```

![Python server](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/python-server.gif)




## Running Locally
We execute the script again and now we got this:

![](https://github.com/cesarvr/hugo-blog/blob/master/static/istio-2/completed-local.gif?raw=true)

We first try using the not-decorated instance service with no telemetry or custom 404 page, then see how executing our "Proxy" process we can add those features.


# Container Oriented Programming

## Before We Start

Here we are going to do some Kubernetes/OpenShift heavy stuff, if you get lost with some buzz word you can take a look at this [getting started guide](https://github.com/cesarvr/Openshift).

## Pod

We finished with the development for now, let's test deploy our creation in Kubernetes/OpenShift. If you remember the [first article](https://cesarvr.io/post/istio/) we build our *pod* using a template that looks similar to this:

```xml
apiversion: v1
kind: Pod
metadata:
  name: my-pod
  labels:
    app: my-pod
spec:
  containers:
  - name: web
    image: docker-registry.default.svc:5000/web-apps/web
    command: ['sh', '-c', 'cd static && python -m http.server 8087']
 - name: proxy
    image: busybox
    command: ['sh', '-c', 'echo Hello World 2 && sleep 3600']
```

We are going to replace the *proxy* container with our service running our application, but first let setup the traffic for this application.



## Exposing Server Ports

We add the port 8087 (the [same port](https://gist.github.com/cesarvr/cecaf693a17b6f09b9eb3f5d38f33165#file-my-pod-yml-L11) the python server running inside the container is using) entry to our *web* container, this way the pod will accept incoming communication and pass it to the server:

```xml
apiversion: v1
kind: Pod
metadata:
  name: my-pod
  labels:
    app: my-pod
spec:
  containers:
  - name: web
    image: docker-registry.default.svc:5000/web-apps/web
    command: ['sh', '-c', 'cd static && python -m http.server 8087']
    port: 8087   #
 - name: proxy
    image: busybox
    command: ['sh', '-c', 'echo Hello World 2 && sleep 3600']
```

We save the template above as ``pod.yml`` and we use it to create our pod:

```sh
 oc create -f pod.yml
```

This template will create two containers.

![](https://github.com/cesarvr/hugo-blog/blob/master/static/istio-2/pod.png?raw=true)

## Sending Some Traffic

Let's send some traffic to our pod.

```sh
  oc create service loadbalancer my-pod --tcp=8087:8087
```

The OpenShift Service object looks for elements in the cluster that match the same label as the name. That's why we named ```my-pod``` as it will automatically look for pods with that label to send some traffic. And we specify port 8087 that match the port we are exposing. Next step is exposing the service, this will setup a router that takes connection coming from outside of the cluster to your OpenShift Service.

```sh
oc expose svc my-pod
```

Now we can access to this particular service with our browser.

![](https://github.com/cesarvr/hugo-blog/blob/master/static/istio-2/pod-svc-routing.gif?raw=true)


We should use a deployment configuration for this but, we are focusing in the understanding of the pod entity.

## Let's Add A Decorator Container

### Making A Container

To make the container I'm going to use the convenient OpenShift [binary build configuration](https://cesarvr.io/post/buildconfig/), this basically delegate the image creation, to OpenShift.

As mentioned before we are going to use an OpenShift builder image, so we need the Node.js version. This version requires we configure the `` package.json`` of our project. We just need to do something like this.

```sh
cd /jump-to-your-script-folder
npm init  # Respond all the questions
```

Open the ``package.json`` and add a **start** entry in the *scripts* section:

```json
{
  "name": "sitio",
  "version": "1.0.0",
  "description": "",
  "main": "app.js",
  "scripts": {
    "test": "echo \"Error: no test specified\" && exit 1",
    "start" : "node app.js"      
  },
  "author": "",
  "license": "ISC"
}
```

The project is now ready to be build:

```sh
  oc new-build nodejs --binary=true --name=decorator
```

Now let's copy the content of our project to the build configuration.

```sh
cd /jump-to-your-script-folder

oc start-build bc/decorator --from-dir=.
#Uploading directory "." as binary input for the build ...
#build "decorator-1" started
```

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/start-build.gif)


Once our application is build, we just need to locate the image created for us:

```sh
oc get is

#NAME        DOCKER REPO                      
#decorator   172.30.1.1:5000/home/decorator
```

And we replace the busybox image we where using this far.

```xml
  ...
  containers:
  - name: web
    image: docker-registry.default.svc:5000/web-apps/web
    command: ['sh', '-c', 'cd static && python -m http.server 8087']
    port: 8087   #
  - name: proxy
    image: 172.30.1.1:5000/home/decorator
```


Also we need to change the port exposed by the pod to 8080, which is the port our "Proxy" container will use.

```xml
apiversion: v1
kind: Pod
metadata:
  name: my-pod
  labels:
    app: my-pod
spec:
 containers:
 - name: web
   image: 172.30.1.1:5000/home/web
   command: ['sh', '-c', 'cd static && python -m http.server 8087']
 - name: proxy
   port: 8080
   image: 172.30.1.1:5000/home/decorator
```

We re-create our pod:

```sh
# Delete
oc delete pod my-pod

# Create
oc create -f pod.yml
```
And here is our decorated container.
![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/decorating%20a%20service.gif)
