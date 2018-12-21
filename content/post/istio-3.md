---
title: "Creating Your Own Istio (Part 3)"
date: 2018-12-11
lastmod: 2018-12-11
draft: true
keywords: []
description: "Reusable Telemetry"
tags: [openshift, container, services, kubernetes]
categories: [openshift, container, services, kubernetes]
toc: true
image: https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/static/logo/profiler.png
---

# Refactoring


The first step to simplify our stuff is to change our in-memory data storage from a dictionary to Array:

```js
class Stats {
 constructor(){
   this.db = [] // from {} to []
   /*..*/
 }

   save(){
     let URL = this.endpoint
     let report = {
       history: this.history(this.db[URL]),
       file: this.isFile(URL),
       pod: this.host()
     }

     this.db.push(report)
 }
}
```

As mentioned before we don't want to maintain a graph per pod anymore, so let's move the content of the ```history``` to the ```save``` method, we just capture the current state at each call a push it into the ```db```.

```js

save(){
  let data = {
   request: { endpoint: this.endpoint, method: this.method },
   response: this.response,
   time: this.end + 'ms',
   started: this.start,
   file: this.isFile(this.endpoint),
   pod: this.host()
 }

 this.db.push(data)
}
```


I also was thinking about the ```resource``` method and I think is better if we keep this method as a separated entity this way we can inform our dashboard at a different rate, you know, the ``save`` data only report per service call and the ``resource`` can report each second, giving us more valuable information, so let's update that method.


```js
resources(){
  return {
    free_memory: this.os.freemem(),
    total_memory: this.os.totalmem(),
    cpus: this.os.cpus()
  }
}
```

The only problem now is how we identify what service is the owner of a group of pods, to solve this we are going create a method that returns the application name:



```js
class Stats {
  /*..*/
  // It transform the pod name ``j-slow-9-5rt8f`` into j-slow.
  name(){
    let host = this.host()      //  j-slow-9-5rt8f
    let tmp = host.split('-')   // [ j-slow, 9, 5rt8f ]

    // remove last two entries
    return tmp.slice(0, tmp.length-2).join('-') // application name: j-slow
  }

  save(){
    let data = {
     name: this.name(), # j-slow,
     request: { endpoint: this.endpoint, method: this.method },
     response: this.response,
     time: this.end + 'ms',
     started: this.start,
     resource: this.resources(),
     file: this.isFile(this.endpoint),
     pod: this.host()
   }

   this.db.push(data)
 }

 resources(){
   return {
     name: this.name(), # j-slow,
     free_memory: this.os.freemem(),
     total_memory: this.os.totalmem(),
     cpus: this.os.cpus()
   }
 }
  /*..*/
}
```

We just simplified the way data is store, let's add some helper methods to maintain the collected.

```js
class Stats {
/*..*/
 size() {
   return this.db.length
 }

 clear() {
   return this.db = []
 }

 get all() {
   return this.db
 }
}
```


### Report

We need now to communicate this data to our central dashboard for this we are going to use a library that handle the HTTP connection for us called ``node-fetch``.

To install the library we just need to use npm:

```sh
  npm install -S node-fetch
```

We are going to replace it, with a function that transmit this data to a central service:

```js
function emit(URL, body) {
  return fetch(URL, {
    method: 'post',
    body:    JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' }
  })
    .then(res => res.json())
    .then(json => console.log(json))
}
```

This function just takes an arbitrary JSON object transform it into string, creates a POST request and send this request to the specified ```URL```. By returning the function call we are returning a [promise](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise).

We are going to a function that execute every 5 seconds and update our *Dashboard* with telemetry from our pod, let's start by writing the backbone:

```js
setInterval(()=> {
  console.log(`reporting queue ${stats.size()} entries`)
  let URL = process.env['DASHBOARD_URL']

}, 5000)
```

We basically are going to fetch the URL for our *Dashboard* URL from the environment variables, now let's implement our HTTP service call.

```js
setInterval(()=> {
  console.log(`reporting queue ${stats.size()} entries`)
  let URL = process.env['MOTHERSHIP']

  if(URL || stats.size() > 0)
    emit(URL, stats.all)

}, 5000)
```

If we got a URL and we have something to report then we call the ``emit`` function, but this can be improved once we send our saved states, we not longer need to keep them in memory, so let's implement a way to clean up after a successful call.

```js
setInterval(()=> {
  console.log(`reporting queue ${stats.size()} entries`)
  let URL = process.env['MOTHERSHIP']

  if(URL || stats.size() > 0)
    emit(URL, stats.all)
      .then(() => stats.clear())
      .catch(err => console.log('dashboard not available'))

}, 5000)
```
The method ``emit`` returns a [promise](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise), we just use it to add more behavior to the request call, in our case we cleared our stats Array and added a function to handle any connectivity error.

With this change we end the work that has to be done in our *decorator* container, we just need to re-deploy this container and forget about it at the moment.

```sh
oc start-build bc/decorator --from-dir=. --follow
```
