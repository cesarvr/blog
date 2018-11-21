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




## What Language

We are going to write our "ambassador container" in Javascript using Node.JS framework, aside from this, you just need an [instance of OpenShift](https://github.com/cesarvr/Openshift#openshiftio) and your favourite editor.

## Making A Tunnel

Let's start by writing a simple proxy application that just takes incoming traffic and pass it to another service. To make things easier I wrote an API called [node-ambassador](https://www.npmjs.com/package/node-ambassador) to avoid cluttering this post with implementation details and keep the focus in the functionalities.

To get the library we can use [npm](https://www.npmjs.com):

```sh
  mkdir /<project-folder>
  cd /<folder-project>

  npm init # creates the package.json
  npm install node-ambassador —save # install library
```

### Incoming Request

We should start by writing a server.

```js
 let { HTTPServer } =  require('node-ambassador')
 let port = process.env['PORT'] || 8080

 function handleConnection(httpConnection) { }

 new HTTPServer({ port, handler: handleConnection )})
 console.log(`Listening for request in ${port}`)
```

To build the server we are going to use the *HTTPServer* class which takes two parameter the *tcp port* where we want to listen and a function (``handleConnection``) that gets call when a new client connects. Also we use the ``PORT`` environment variable to setup alternative port.

The ``httpConnection`` object triggers the ``server:read`` event to inform of any traffic coming our way, we just need to subscribe to it.

```js
/*...*/
function handleConnection(httpConnection) {
  httpConnection.on('server:read', incomingData => console.log(incomingData))
}
/*...*/
```

If we execute the script a server will be created and if we connect the browser to port 8080 we should get this:

```xml
GET / HTTP/1.1
Host: localhost:8080
Connection: keep-alive
Cache-Control: max-age=0
....
```

### Passing The Request

We got one part of the bridge, so now let's take care of the part that delivers the incoming data to its destination.

To do this we need to import the *HTTPService* class, that like the class above handles the complexity but this time from the service side (the destination).

```js
  let { HTTPService, HTTPServer } =  require('node-ambassador')

  function handleConnection(httpConnection) {
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

But this bridge works in one direction because we need to implement the response from **the service** to  **the client**. To do this we can take advantage that *HTTPService* includes event called ``service:read`` so we can know when a TCP response is delivered.

The bi-directional bridge will look something like this:

```js
function handleConnection(httpConnection) {
  let service = new Service({port: process.env['PORT'] || 8087})

  // Tunnel
  httpConnection.on( 'server:read',  data => service.send(data) )
  service.on('service:read', data => httpConnection.send(data)  )
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

## More Than Just Proxy

At this stage we just got a simple proxy server, now we are going to build some functionalities on top of this proxy so other services implement it.

### Overriding Responses

Let's write some code to override the default web server 404 page of our python web server.

We can start by defining a new 404 page using this [constant string](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals).

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

In the typical scenario a HTTP client opens connection and send us a request, we proxy it to the service and when the service responds we need to read the HTTP status code and take an action accordingly.

To handle incoming traffic we are using the *HTTPService* class, but this class does more than that, if the request contains an HTTP header it triggers the event ``service:response:{HTTP_status}`` containing the status and the HTTP payload and this is exactly what we need to create specific responses.

```js
 service.on('service:response:500', response => if_friday_kill_process(response) )
 service.on('service:response:200', response => send_congratulations )
```

We just need to subscribe to the `404` event and send the string if when this condition occurs. Next thing we need is to send the response, doing this we need to use the *HTTPServer* method [HTTPServer.respond](https://www.npmjs.com/package/node-ambassador#httpconnection), by using this method we cut the proxied response to send ours.

```js
const HTTP404 = `...`

function handleConnection(httpConnection) {
  //...
  service.on('service:response:404', response => httpConnection.respond([HTTP404]) )
  //...
}
```

Now we got a proxy, but if for some reason the browser ask for a non-existing resource we override the response with our solid enterprise grade response.

![proxy-v2](https://github.com/cesarvr/hugo-blog/blob/master/static/istio-2/proxy-v2.gif?raw=true)

### Network Profiling

This is a very useful use case for the Ambassador pattern, as proved by the arrival of "services meshes" everywhere. I personally don't like to write time sampling algorithms inside my business classes, with containers and Kubernetes this type of behaviour can even be isolated in its own container as we are going to observe.

The strategy we are going to take to make our network profiler, is to take advantage of our man in the middle situation to analyse the traffic passing through our proxy.

#### Tracking Endpoints

To make our profiler we first need to know what URL resource the client is trying to access, to get this information we are can subscribe to an event provided by the *HTTPServer* class called *[server:http:headers](https://www.npmjs.com/package/node-ambassador#events-1)*, this event gets trigger any time a HTTP header is detected, giving us the following header object:

```js
{
  HTTPMethod,   //HTTP Method   -> GET
  HTTPResource  //HTTP Resource -> /home
}
```

We are going to create a class called *Stats*, with the method ``readRequest`` to read and persist the state of the HTTP request header.

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

We subscribe this method to the *[server:http:headers](https://www.npmjs.com/package/node-ambassador#events-1)* event also to persist the state we are going to initialise our new *Stat* object outside of the scope of the function. We are returning an instance of the same class this is just to allow us to chain methods.

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


#### Timing

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

As you might notice in the return type of the methods is an instance of the class, this is handy so we can chain the calls and minimise the clutter.


### In-Memory DataBase and Calculations

To make our *Stat* class useful we are going to keep a registry of the service usage, to persist this data we are going to create a "sophisticated" in-memory database by using this Javascript object to collect the data.

```js
class Stats {
  constructor(){
    this.db = {}
  }
}
```

Now let's take care of the calculations, for this we are going to expose a new method called ``new_entry``, when this method gets called we perform some calculations and save the state of the object. This calculations include time average, hit count, historic calls, etc.


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
    entry.avg    =  Math.round((this.end / entry.hit) * 100) / 100 + 'ms' // truncating
  }



  get all(){
    return this.db
  }

  /*..*/
}
```

Next we are going to call this method just after the service has responded, this way we get information from all the circuit.

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

After we run our proxy we try to call some URL and after 5 seconds we start getting the usage data:

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

We are getting this information by proxy the information to a local Python server, the next step is to pack this process into a container and the perform the same functionalities 404 included with any other service running in our same logical host (IP address or pod).

## Deploying

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

![my-pod](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/deploy-1.png)

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


### Decorating Java Micro-services

Here is a quick video showing how to by using this steps we can enhance a Java micro-service, with newly developed telemetry and with an enterprise grade 404 page.  

![](https://raw.githubusercontent.com/cesarvr/ambassador/master/assets/final.gif)


## Wrapping Up

Of course our container is (still) light years away to catch up with *Istio*, but after reading you should be able to develop and reuse application using the patterns like the ambassador, side-car, etc. To improve legacy or current services without touching the code.

In the next post I'm going to implement a central point to control all our the containers, so we can implement some cool ideas, like shutting down an endpoint by just sending a signal from a dashboard.

Feel free to contribute to the ```node-ambassador``` API, features and improvement are much welcome.
