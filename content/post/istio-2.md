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
Services that implement our reusable container will be capable of this 3 features:

- Get usage frequency, how many time a endpoint is being called.
- Get Response time.
- Override 404 Page with a custom one.

# TCP/Server

The first feature our container need to be able to do is to talk the same dialect that our services, in our "service mesh", let assume that all our services talks using the HTTP protocol.  

For flexibility we are going to create a TCP/Server, because is the minimum common denominator and because we want to retain the integrity of the incoming calls.

```js
var net = require('net')

console.log('Listening for request in 8080')
net.createServer( function (socket) {
  console.log('new connection!')
  socket.end()
}).listen(8080)
```

This code as we mention before is the [Node.js](https://nodejs.org/en/) way to create a simple TCP server, feel free to re-write this code in your favourite language.

We are going to name this file as ```sitio.js``` and run this script with:

```sh
node sitio.js
# Listening for request in 8080
```

Calling in our browser will give us this response:

![](https://github.com/cesarvr/hugo-blog/blob/master/static/istio-2/empty-response.png?raw=true)

Notice that say *empty response* this mean that we are connecting but doing nothing. Let's write our first feature!.

# Usage frequency

## Input/Output 

Before we can measure we need to write some boilerplate code to handle the I/O of our server socket.

```js
var net = require('net')


function read(data) {
  console.log(data.toString())
}

function handle(socket) {
  socket.on('data', read)
}

console.log('Listening for request in 8080')
net.createServer( function (socket) {
  console.log('new connection!')
  handle(socket)
}).listen(8080)
```

In[Node.js](https://nodejs.org/en/) the I/O is handled by events, instead of blocking the file descriptor we just wait for the OS to notify when data is available. To handle when *data* is available in the socket we pass the *read* function, this then print to the [stdout](http://www.linfo.org/standard_output.html).

```#!/bin/sh
node app.js

# GET / HTTP/1.1
# Host: localhost:8080
# ....
```

## Parsing HTTP 
 
After we handle the I/O, we can write a function to extract the endpoint from that HTTP header.

```
function extractURL(http_block) {
  let str = http_block.split('\n')[0]

  return str.replace("GET", "")
    .replace("HTTP\/1.1","")
    .trim()
}
```

Here we just focus in the first line of the [HTTP request header](https://developer.mozilla.org/en-US/docs/Glossary/Request_header), and extract the request URL.

We just parse this ```sh GET /hello HTTP/1.1 ``` to get this ```/hello```.

Once we got the URL, next step is to implement an algorithm to persist the URL entries. This quick and dirty key-store in memory database will do the job.

```js
let track = function() {
  let db = {}
  return {
    save: function(key) {
      if( db[key] === undefined )
        db[key] = 1
       else
        db[key]+= 1
    },
    all: function(){
      return db
    }
  }
}() 
```

We edit the function in charge of I/O: 

```js
function read(data) {
  let str_data = data.toString()

  // parsing the HTTP Header
  let endpoint = extractURL(str_data)

  // save URL route   
  track.save(endpoint)

  console.log('endpoint: \n', track.all() )
}
``` 

We put this together:

```js
var net = require('net')

let track = function() {
  let db = {}
  return {
    save: function(key) {
      if( db[key] === undefined )
        db[key] = 1
       else
        db[key]+= 1
    },
    all: ()=>{
      return db
    }
  }
}()

function extractURL(http_block) {
  let str = http_block.split('\n')[0]

  return str.replace("GET", "")
    .replace("HTTP\/1.1","")
    .trim()
}

function read(data) {
  let str_data = data.toString()

  // parsing the HTTP Header
  let endpoint = extractURL(str_data)

  // save URL route   
  track.save(endpoint)

  console.log('endpoint: \n', track.all() )
}

function handle(socket) {
  socket.on('data', read)
}

console.log('Listening for request in 8080')
net.createServer( function (socket) {
  console.log('new connection!')
  handle(socket)
}).listen(8080)

```

We run our application again, to see the new changes: 

```
node app.js

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

When we browse ```localhost:8080``` our process is able to gather usage information. Now let's see how we can reuse this nice feature with other services.

# Reusing Features

If you execute this command:

```sh
  python -m SimpleHTTPServer 8087
```

Python will create a simple web server and will serve the folder from your call this command from.  

To delegate the request to other service we are going to create a TCP Socket pointing to service we want to delegate the request to.

```js
let delegate = function(port){
  let client = new net.Socket()
  client.connect(port || 8087, '0.0.0.0', function() {
    console.log(`connected to ${port}`)
  })
  return client
}
```
This function just connect to the localhost using a TCP Socket, through the port we specify in the function parameter.

Let revisit function that handles the socket server.

```js
function handle(socket) {

  socket.on('data', read)

}
```

The first thing we want to do is that any time we got a new connection, we need to delegate and to delegate we need to open a new connection to the service, so let's write that.

```js
function handle(socket) {

let client = delegate(8087)

socket.on('data', data => client.write(read(data)))
}
```

We receive some data from the server socket, we perform our task (measuring) and we delegate to the next service. Now we need to allow the service to respond, otherwise the caller of the service will wait forever.

We can do this by "reverting" the operation, or basically delegate every data coming from the service to the caller.


```js
client.on('data', data => socket.write(data))
```

This delegate all packets to the one calling the service. The final version look like this:


```js
function handle(socket) {

  let client = delegate(8087)

  socket.on('data', data => client.write(read(data)))
  client.on('data', data => socket.write(data))
  socket.on('end', end => client.end())
  socket.on('close', end => client.end())
}
```
