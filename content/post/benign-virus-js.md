---
title: "Self Deploying Node.JS Applications"
date: 2019-02-20
lastmod: 2019-02-20
draft: true
keywords: []
description: "Let's write an application that runs itself into OpenShift."
tags: [openshift, container, services, kubernetes]
categories: [openshift, container, nodejs, kubernetes]
toc: true
image: https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/static/logo/js.png
---

The motivation for this article is that, i wanted to develop a library to basically enhance the runtime capabilities of a Node.js script without bothering the user with configurations and stuff like that, so the goal for this library is that it need to be invisible in normal execution and expose an entry point via a ``flag`` like ``-c`` that perform this enhancement for the user.


## Infecting

As mentioned above this virus need to be inoculated in some way, so let make it a module and I decided to call it ``okd-runner``, let's see how we can take control of execution by creating a simple file.

We can start by creating a simple module called ``bening.js``:

``js
let runtime = function() {
  console.log('I execute first')
}()

module.exports = runtime
``

To test our module we are going to create a new application and add the library:

```js
require('./benign-js')

console.log('Hello')
```

If we run this we get the following:

```sh
  I execute first
  Hello
```






after all I just want to replace the local JS virtual machine with a JS running inside a container somewhere in the cloud.
