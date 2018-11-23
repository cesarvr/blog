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

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/java-intro.gif)

What you see here is the deployment of the [Java "Hello World" template](https://github.com/openshift/openshift-jee-sample.git) in OpenShift which provides a welcome page, but a closer look will tell you that this application has other features like a network profiler (right section) and also implements an enterprise ready 404 page.

## How Does It Work ? 

The Java application running as usual, but in reality, a Node.js process is acting as a middleware performing some task on its behalf. Though two processes share the same [pod](https://docs.openshift.com/enterprise/3.0/architecture/core_concepts/pods_and_services.html) they run in different containers.

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/design.svg?sanitize=true)


This is what you call an ["Ambassador pattern"](https://ai.google/research/pubs/pub45406). In this post we are going to focus on how to make use of this pattern to encapsulate and share behaviour across services.

## Before We Start 

To write our "ambassador" process we are going to use Javascript/Node.JS, which give us a very high level language. If you want to follow the instructions you will need to setup an [OpenShift instance](https://github.com/cesarvr/Openshift#openshiftio) and your favorite text editor.

# Writing A Proxy Server 

Let's start by writing a proxy server, which takes incoming TCP traffic and send it to another process. To make things easier I wrote an API called [node-ambassador](https://www.npmjs.com/package/node-ambassador).

You can get the library with [npm](https://www.npmjs.com):

```sh
  mkdir /<project-folder>
  cd /<folder-project>

  npm init # creates the package.json
  npm install node-ambassador --save # install library
```

## Incoming Request

Let's use this library to develop a HTTP server.

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/first.png)

### Configuration   

To start a server we just need to instantiate the *HTTPServer* class and setup a **tcp port** 8080. 

```js
 let { HTTPServer } =  require('node-ambassador')
 let port = process.env['PORT'] || 8080

 new HTTPServer({ port, handler: () => {} )})
 console.log(`Listening for request in ${port}`)
```

The ``process.env`` read the value TCP port value from environment variables.


### Handling New Connections

The *HTTPServer* constructor expects a function to handle any new connection.

```js
/*...*/
function handleConnection(httpConnection) {
}

new HTTPServer({ port, handler: handleConnection )})
/*...*/
```

This function receive as parameter a ``httpConnection`` object, this object takes care of the I/O from the client side. 

### Reading Incoming Traffic

To handle data coming our way we need to subscribe to the ``read`` event: 


```js
/*...*/
function handleConnection(httpConnection) {
  httpConnection.on('read', (data) => console.log(data))
}
/*...*/
```

If we execute the script we should see something like this when we connect with the browser:

```xml
Listening for request in 8080

GET / HTTP/1.1
Host: localhost:8080
Connection: keep-alive
Cache-Control: max-age=0
....
```

## Proxy The Request

Let's take care of the part that delivers the incoming data to its destination.

### More Configuration   

We can start by importing the *HTTPService* class and configuring the target port. 

```js
  let { HTTPService, HTTPServer } =  require('node-ambassador')

  function handleConnection(httpConnection) {
    let service = new HTTPService({port: process.env['PORT'] || 8087})
    /...
  }
  /...
```

This follow the same configuration as the *HTTPServer*, but targeting now a running service.


### From Client To Service   

To send some data to the connected service we are going to use the ``send`` method. 

```js
  service.send(data)
```

We connect this method to the server's ``read`` event and we are done.

```js
  server.on('read', data => service.send(data))
```

### From Service To Client 

Both classes *HTTPServer* and *HTTPService* share the same interfaces for I/O, to reverse the communication flow we just need to write the reverse operation.


```js
function handleConnection(httpConnection) {
  let service = new Service({port: process.env['PORT'] || 8087})

  // Tunnel
  httpConnection.on( 'read',  data => service.send(data) )
  service.on('read', data => httpConnection.send(data)  )
}
```

### Testing

To test our proxy we just need to run a process in the same IP capable of understanding the HTTP version 1.+) protocol, to make it simple we are going to use Python [simple server module](https://docs.python.org/2/library/simplehttpserver.html) as our test suite.

To serve a folder and assuming we have python installed, we just run the following command:

```sh
  python -m SimpleHTTPServer 8087
```

This server will use the *port 8087* to serve its contents.

To execute our script we need to configure the environment variables, ``TARGET_PORT`` to target the Python server and ``PORT`` the TCP port we want to listen to.

```sh
export PORT=8080
export TARGET_PORT=8087

node app.js
```

![proxy-v1](https://github.com/cesarvr/hugo-blog/blob/master/static/istio-2/proxy-v1.gif?raw=true)

## More Than Just Proxy

At this stage we just got a simple proxy server, now we need to build something on top of it, so other service can *inherit it*.

### Overriding Responses

This can be interesting to redefine a behaviour for a service response, let's say you want to return a new kind of Base64 encoded string error message/cause so you user can copy paste in case of trouble, instead of re-writing and re-implementing this behaviour everywhere just add the algorithm to your "ambassador" container and let it override the response for all your services. 

To demonstrate this, let's create a 404 replacement page. 

We can start by defining a 404 page using this [constant string](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals).

```js
const HTTP404 = `
HTTP/1.0 404 File not found
Server: Sitio 💥
Date: ${Date()}
Content-Type: text/html
Connection: close

<body>
  <H1>Look Somewhere Else /  Not Found</H1>
  <img src="https://www.wykop.pl/cdn/c3201142/comment_E6icBQJrg2RCWMVsTm4mA3XdC9yQKIjM.gif">
</body>`
```

To handle incoming traffic we are using the *HTTPService* class, but this class can do more than that, if the request contains an HTTP header it triggers the event ``service:response:{HTTP_status}`` containing the HTTP status code. 

Take a look at the following implementation examples: 

```js
 service.on('service:response:500', response => if_friday_restart_process(response) )
 service.on('service:response:200', response => send_congratulations )
```

We just need to subscribe to the ``404`` event and use the [HTTPServer.respond](https://www.npmjs.com/package/node-ambassador#httpconnection) method. This method stops the **client to service** flow and override the response.

```js
const HTTP404 = `...`

function handleConnection(httpConnection) {
  //...
  service.on('service:response:404', response => httpConnection.respond([HTTP404]) )
  //...
}
```

![proxy-v2](https://github.com/cesarvr/hugo-blog/blob/master/static/istio-2/proxy-v2.gif?raw=true)

### Network Profiling

The strategy we are going to follow to make our profiler, is to take advantage of our man in the middle situation to analyse the traffic. By reading this information we can know the latency, detect errors, report on service status, payload size, etc.  

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

## Deploying

### Before We Start

Now we are going to take dive in some Kubernetes/OpenShift stuff, so if you get lost with some *buzz words* you can get up to speed by looking at this [getting started guide](https://github.com/cesarvr/Openshift) or if you have any doubt about some advanced pod deployment you can check the [first part](https://cesarvr.io/post/istio/) of this series.

### Running A Service

If you remember the [first article](https://cesarvr.io/post/istio/) we build our *pod* using this simple template:

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
    port: 8087  # <---- here  
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

Our service is ready to receive external traffic.

![](https://github.com/cesarvr/hugo-blog/blob/master/static/istio-2/pod-svc-routing.gif?raw=true)


> We should use a deployment configuration for this but our focus is the understanding of the Kubernetes pod.

### Making Our Application *Cloud Native*

It's time for our application to be deployed in somebody else computer, there is many ways to do this but at the moment I feel more confortable with OpenShift [build configuration](https://cesarvr.io/post/buildconfig/). This entity basically delegates the project setup and image creation to a remote machine managed by the platform.

This builder configuration requires that our Node.js project includes a ``start`` entry, this way the image container can be executed with [npm start](https://docs.npmjs.com/cli/start).

Open the ``package.json`` and add a **start** entry inside the *scripts* section:

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

Now we can create our NodeJS binary build configuration:

```sh
  oc new-build nodejs --binary=true --name=decorator
```

Build our project, this will create a immutable image.

```sh
cd /jump-to-your-script-folder

oc start-build bc/decorator --from-dir=.
#Uploading directory "." as binary input for the build ...
#build "decorator-1" started
```


![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/start-build.gif)


Locate the created image using the ``oc get is`` command:

```sh
oc get is

#NAME        DOCKER REPO                      
#decorator   172.30.1.1:5000/home/decorator
```


At this moment we have to options, the first option is to apply ``oc edit pod <name-of-your-pod>`` and replace the ``buxybox`` value with the ``DOCKER REPO`` URL from above, but sometimes editing those templates can be scary task. 

Your second option is to go to the template we used before and replace the ``busybox`` in the ``image`` section with ``172.30.1.1:5000/home/decorator``, then recreate the resources.  

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

Also we are interested in demonstrating that we can add our ambassador container without causing any problem to the main container. At the moment we got something that looks like this: 

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/before.svg?sanitize=true) 

We added the ambassador container, now the next thing we need is to change the pod's exposed port so it reflect the ambassador container 8080.

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
   # move the port from here
 - name: proxy
   port: 8080    # to here, and change 8087 to 8080.
   image: 172.30.1.1:5000/home/decorator
```

The Node.js process will take care of finding the Python port once it gets deployed giving us this result.

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/after.svg?sanitize=true)


We delete the route, services and pods:

```sh
# Delete services and route
oc delete svc my-pod
oc delete route my-pod
oc delete pod my-pod

```

We recreate it again: 


```sh 

# Recreate
oc create -f pod.yml
oc create service loadbalancer my-pod --tcp=8080:8080
oc expose svc my-pod
```

We don't necessary need to delete the services or routes, but as mentioned before this way I think is more clear.

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/istio-2/decorating%20a%20service.gif)


> You just need to create robot that does this add/remove automatically.


### Decorating Java Micro-services

Here is a quick video showing ambassador container with a Java micro-service.  

![](https://raw.githubusercontent.com/cesarvr/ambassador/master/assets/final.gif)


## Wrapping Up

If you think about it this what we just did was encapsulating behaviour in a container and make it reusable across a system of processes that communicates using a common protocol, this idea is very powerful and not that different in essence to the objects oriented paradigm we are use to. 

One thing missing is to implement a central point to control all our ambassador containers, it won't be cool to have a dashboard from where to shutdown an endpoint, those are some of the ideas I'll try to incorporate in the next chapter. 

One last thing, feel free to contribute to the ```node-ambassador``` API, with any missing features, improvement, etc. 
