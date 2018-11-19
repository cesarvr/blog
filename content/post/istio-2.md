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

In the last post we learn that the minimal deployment unit in Kubernetes/OpenShift is the pod and that this entity provides an isolation similar to the one provided by containers, we took advantage of this to deploy multi-tier applications. Knowing this alone can be very beneficial to deal with your day to day complexity, but is time to take another step forward and learn how we can create processes that modify or enhance other services.

For this process to be useful it need to have the following characteristics:
- It need to run in its own container.
- It need to understand the protocol of the service.  
- It should keep the integrity of the communication, the running service should be unaware of its existence of our process.

This set of functionalities are part of the definition of an ambassador pattern, for short we are going to call our process the proxy container.



## Getting Started

To make this accessible we are going to write our process in beautiful Javascript language, using Node.JS framework. The only thing you need to follow this post is to install OpenShift, Node.js and editor like vim, emacs, etc.

## Making A Tunnel

We can start by writing a simple Proxy application that basically takes traffic coming from a tcp client (like a browser) and pass this traffic untouched to another service. Basically we need to create a bridge between the two, so to make this I wrote a simple API called [node-ambassador](https://www.npmjs.com/package/node-ambassador) to take some boilerplate away.

To get the library we just need to use [npm](https://www.npmjs.com):

```sh
  mkdir /folder-project
  cd / folder-project
  npm init # creates the package.json
  npm install node-ambassador —save # install library
```

### Incoming Request

Let's write some code to handle the incoming traffic:

```js
let { HTTPServer } =  require('node-ambassador')

new HTTPServer({port: 8080, handler: fn})
console.log('Listening for request in 8080!!')
```
We instantiate the *HTTPServer* class, this class takes two parameter the *tcp port* from where to receive traffic and function handler that gets call when a new client connects.

```js
  function handleConnection(server) {  }

  let port = process.env['PORT'] || 8080
  new HTTPServer({port, handler: handleConnection})
  console.log(`Listening for request in ${port}!!`)
```

When a client connects, the function is injected with a *HTTPSocket* object which encapsulates some useful methods and events to deal with HTTP/TCP I/O from connected client. We also using ``process.env`` to retrieve the port number from the environment variables, this will give us some flexibility.

To listen when data is coming our way we are going to use the ``server:read`` event:

```js
/*...*/
function handleConnection(server) {
  server.on('server:read', incomingData => console.log(incomingData))
}
/*...*/
```

If we execute the script it will create a server, if we connect the browser to port 8080 we should get this:

```xml
GET / HTTP/1.1
Host: localhost:8080
Connection: keep-alive
Cache-Control: max-age=0
....
```

### Passing The Request

We got one part of the bridge, so now let's take care of the part that delivers the incoming data to its destination.

For this we need to import the *HTTPService* class, that like the class above handles the complexity but this time from the service side (the destination).

```js
let { HTTPService, HTTPServer } =  require('node-ambassador')

function handleConnection(server) {
  let service = new HTTPService({port: process.env['PORT'] || 8087})
  /...
}
  /...
```

We just need to provide the port where the service we want to target is running.   

To send some data to the connected service we are going to use the ``send`` method, if we connect this method to the server's ``server:traffic`` event we got our bridge from **the client** to **the service**.

```js
  server.on('server:traffic', incomingData => service.send(incomingData))
```

But this bridge works in one direction only, meaning that we need to recover the response from **the service** to send it back to **the client**. To do this we can take advantage that *HTTPService* includes event called ``service:read`` so we can know when a TCP response is delivered.

The bi-directional bridge will look something like this: 

```js
function handleConnection(server) {
  let service = new Service({port: process.env['PORT'] || 8087})

  // Tunnel
  server.on( 'server:read',  data => service.send(data) )
  service.on('service:read', data => server.send(data)  )
}
```

### Testing

To test our proxy we just need to run a process in the same IP that understand the HTTP protocol, to make it simple we are going to use Python [simple server module](https://docs.python.org/2/library/simplehttpserver.html).

To serve a folder and assuming we have python installed we can run the following command:

```sh
  python -m SimpleHTTPServer 8087
```

This server will use the *port 8087* to serve its contents.

To execute our script we need to configure the environment variables.

```sh
export PORT=8080
export TARGET_PORT=8087

node app.js
```

And we should get our proxy running.


![proxy-v1](https://github.com/cesarvr/hugo-blog/blob/master/static/istio-2/proxy-v1.gif?raw=true)


## Adding New Features

Imagine if we have the ability to enhance any service with new features like detecting HTTP when a service goes wrong and raising a email to somebody, or we can implement a robot to look for patterns like "Error!", "Died", "Help" in the logs and raise an alarm. The fact of being capable of doing things like this is what makes the techniques we are going to learn so cool.

### Overriding Responses

By overriding responses I mean to change the default response of a particular service, to give you an example let's write some code to override the default web server 404 page of our python web server.

We can start by defining a new 404 page using this [constant  string](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals).

```js
const HTTP404 = `
HTTP/1.0 404 File not found
Server: Sitio 💥
Date: ${Date()}
Content-Type: text/html
Connection: close

<body>
  <H1>Endpoint Not Found</H1>
  <img src="https://www.wykop.pl/cdn/c3201142/comment_E6icBQJrg2RCWMVsTm4mA3XdC9yQKIjM.gif">
</body>`
```

In the typical scenario the browser or other service send us a request, we proxy it to the service and when the service we need to read the HTTP status code and if this code is 404 we replace the response with our string. To check the response status code we can use the *HTTPService* class which includes events for each HTTP status code, by using this notation ``service:response:{status}`` and handle each situation with a function.

```js
 service.on('service:response:500', response => if_friday_kill_process(response) )
 service.on('service:response:200', response => send_congratulations )
```

We just need to subscribe to the `404` event and send the string if when this condition occurs.

```js
const HTTP404 = `...`

function handleConnection(server) {
  //...
  service.on('service:response:404', response => server.respond([HTTP404]) )
  //...
}
```

![proxy-v2](https://github.com/cesarvr/hugo-blog/blob/master/static/istio-2/proxy-v2.gif?raw=true)

## Profiling

This is a very useful use case for the Ambassador pattern, as proved by the arrival of "services meshes" everywhere. Profiling is the typical problem I don't want my business classes to know nothing about, for that reason it makes a perfect candidate to live in its own isolated container. We are going to write a very simple service network profiler.

### Tracking Endpoints

To make our profiler we first need to know what is the resource the browser or client is trying to access, to get this information we are going to subscribe to the *HTTPSocketServer* event called ``server:http:headers``. When this method get triggered we are going to get a object with some HTTP header information. 

```js
{
  method,   //HTTP Method   -> GET
  endpoint  //HTTP Resource -> /home
}

``` 

We are going to create a class called *Stats*, with the method ``readRequest`` to read the request information.

```js
class Stats  {

  constructor(){
    this.db = {}
  }

  readRequest(header){
    this.method   = header.HTTPMethod
    this.endpoint = header.HTTPResource

    return this
  }
}
```

Next step is to hook instantiate the class and hook the method to the event listener.

```js
let stats = new Stats()

function handleConnection(server) {
  /*...*/
  let service = new HTTPService({port: tport })

  server.on('server:http:headers',   
                          (header, data) => stats.readRequest(header)
                                                   .start_profile() )
  /*...*/
}
```
To persist the state we are going to initialise our new *Stat* object outside of the scope of the function.

### Timing

For the timing we are going to create two methods one handling the beginning of the service transaction (``start_profile``) and other taking a time sample when we got the response (``end_profile``).

```xml
  latency = response_time - delivering_time
```

Let's implement this idea.

```js
class Stats  {

  //...
  start_profile(){
    this.start = new Date().getTime()
    return this
  }

  end_profile() {
    this.end =  new Date().getTime() - this.start
    return this
  }
  // ...
}
```

We save this values in the object at the moment.

```js
let stats = new Stats()


function handleConnection(server) {
  /*...*/
  server.on('server:http:headers',   
                          (header, data) => stats.readrequest(header)
                                                 .start_profile() )

  service.on('service:http:headers', (header, data) =>stats.end_profile() )
}
```

As you might notice in the return type of the methods is an instance of the class, this is handy so we can chain the calls and minimize the event subscription.


### In-Memory DataBase and Calculations

To make our *Stat* class useful we are going to keep a registry of the service usage, to persist this data we are going to create a "sophisticated" in-memory database.

```js
class Stats {
  constructor(){
    this.db = {}
  }
}
```

We are going to make use of a JS object (which is equivalent to a hash-map or dictionary). Now let's take care of the calculations, for this we are going to expose a new method called ``new_entry``, when this method gets called we save the state of the object.


```js
class Stats  {

  constructor(){
    this.db = {}
  }

  new_entry(){
    let key = this.endpoint
    let entry = undefined

    // if the entry doesn't exist, instantiate a new object
    this.db[key]      =  this.db[key] || {}

    entry = this.db[key] // we retrieve the object by reference.
    entry.hit  = entry.hit || 0
    entry.avg  = entry.avg || 0
    entry.total = entry.total || 0
    entry.history = entry.history || []

    entry.hit += 1
    entry.total += this.end
    entry.history.push({time: this.end + 'ms', method:this.method, response: this.response })
    entry.avg =  Math.round((this.end / entry.hit) * 100) / 100 + 'ms' // truncating
  }



  get all(){
    return this.db
  }

  /*..*/
}
```
In this method we handle some boring calculations to make this profiler competitive in the *"service mesh"* market. And we provide a method ``all`` to retrieve the content of our in-memory database. We just need to hook this method to the *Service* response event.



```js
function handleConnection(server) {
  /*...*/
  server.on('server:http:headers',   
                          (header, data) => stats.readrequest(header)
                                                 .start_profile() )

  service.on('service:http:headers', (header, data) => 
                                                 .end_profile()
                                                 .new_entry() )
  /*...*/
}

```

To make this information available for us to read, let's create some kind of 5 seconds refresh to show the data collected through standard output. In the next post we are going to replace this with a dashboard.

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

After we run our service we start our report:

```json
{
	"/": {
		"hit": 3,
		"avg": "0.33ms",
		"total": 9,
		"history": [{
			"time": "5ms",
			"method": "GET"
		}, {
			"time": "3ms",
			"method": "GET"
		}, {
			"time": "1ms",
			"method": "GET"
		}]
	},
	"/home": {
		"hit": 1,
		"avg": "8ms",
		"total": 8,
		"history": [{
			"time": "8ms",
			"method": "GET"
		}]
	}
}
```

## Container Decorator

### Before We Start

Here we are going to do some Kubernetes/OpenShift heavy stuff, if you get lost with some *buzz words* you can get up to speed by looking at this [getting started guide](https://github.com/cesarvr/Openshift).

### Running A Service

Let's test deploy our creation in Kubernetes/OpenShift. If you remember the [first article](https://cesarvr.io/post/istio/) we build our *pod* using this simple template:

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

This pod deploys a container with a python runtime, then it runs a python web server very similar to the one we have been using so far.

## Exposing Server Ports

This web server is using [port 8087](https://gist.github.com/cesarvr/cecaf693a17b6f09b9eb3f5d38f33165#file-my-pod-yml-L11), this mean we need tell the pod to expose this port by including it inside the container definition.

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
    port: 8087  # here  
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

The [OpenShift Service](https://github.com/cesarvr/Openshift#service) represents a load balancer that we can configure to send traffic to our application. By choosing the same name ``my-pod`` it will automatically look for pods with that name and direct traffic to them using port 8087.

Next step is creating a route:

```sh
oc expose svc my-pod
```

Our service is now published.

![](https://github.com/cesarvr/hugo-blog/blob/master/static/istio-2/pod-svc-routing.gif?raw=true)


We should use a deployment configuration for this but our focus is in understanding of the pod entity, and doing it as simple as possible.

### Making Our Application "Cloud Native"

It's time for our application to be deployed in somebody else computer, there is many ways to do this but my expertise at the moment is doing it with OpenShift [binary build configuration](https://cesarvr.io/post/buildconfig/), this basically delegate the image creation to OpenShift using its Node.js builder image.

This builder configuration requires that our Node.js project includes a ``start`` entry, this way the image container can be executed with [npm start](https://docs.npmjs.com/cli/start).

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

Now we can create our NodeJS build configuration:

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

We comeback to our template and replace the busybox image we where using so far.

```xml
  ...
  containers:
  - name: web
    image: docker-registry.default.svc:5000/web-apps/web
    command: ['sh', '-c', 'cd static && python -m http.server 8087']
    port: 8087   #
  - name: proxy
    image: 172.30.1.1:5000/home/decorator # replace busybox, with the URL returned by oc get is.
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

We delete the route, services and pods:

```sh
# Delete services and route
oc delete svc my-pod
oc delete route my-pod

# Delete
oc delete pod my-pod

# Recreate
oc create -f pod.yml
oc create service loadbalancer my-pod --tcp=8080:8080
oc expose svc my-pod
```

We don't necessary need to delete the services or routes, but in our case recreate this objects is easier than edit this object.

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/decorating%20a%20service.gif)

As you see we are executing a different application from the one we tested here.

## Wrapping Up

Of course our container is light years away to catch with the *Istio*, but after reading you should be able to create you own reusable containers. Some good ideas to apply this is security, let say you have Keycloak and you want all your services to support it, do you prefer to write a module for all your services or you prefer to write a modular and reusable container that apply those rules transparently, I'll sure prefer the later option.

In the next post we are going to implement a simple dashboard to get some information also, I thinking to add some remote control capabilities, like remotely shutting down a endpoint or maybe demoing some circuit breaker pattern.

Also feel free to contribute to the ```node-ambassador``` API, features and improvement are much welcome.  
