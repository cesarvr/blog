---
date: "2015-11-20T00:00:00Z"
title: Embedding Javascript v8
categories: [JavaScript, C, C++]
---

# Building V8 Javascript Engine.


### Introduction

I was thinking sometime ago about starting hacking with V8, aside from the fact that I work every day with Javascript, is that the Chromium engineers are doing a very good job making V8 fast and efficient and for some task good Javascript code is faster than C++, here is a great talk about the sophisticated JIT generation in Javascript.

After many days of procrastination, I put my hands-on and start the task of downloading the project and prayed that everything would just work, like many things in life it didn't work the first time, here I documented all the steps, if somebody wants to start playing with this, hopefully this will make their life easy.  

For my hacking session I just make a VM based in Archlinux, but the same step could apply to other Linux Distributions.   

### Building.


First we need is to install Git and install the all necessary build tools in others dist is called build-essentials in arch is called base-devel.

```sh
$ pacman -Sy base-devel git
```

Now we need to download from Chromium project their specific tool depot_tools, this will allow us to checkout specifics projects from their repo in this case V8, then we add this directory to our PATH.

```sh
$ git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
$ export PATH=$PWD/depot_tools:$PATH
```

If you had python2 by default jump this step, in my case Arch came with Python3 by default so i need to re-direct the global /usr/bin/python to point the /usr/bin/python2.

```sh
$ ln -s /usr/bin/python2 /usr/bin/python
$ ln -s /usb/bin/python2-config /usr/bin/python-config
```

For 64 bits machine like mine I need to made a symlink to libtinfo.so.5

```sh
$ ln -s /usr/lib/libncurses.so.5.7 /lib64/libtinfo.so.5
```

If everything go is fine now you should be able to execute gclient from console.

```sh
$ gclient config url-v8-git-project
```

This make a folder in your root dir named v8, this could be done better but I’m using a virtual machine, so no problem.

go inside the created dir /home/user/v8 in my case.

```sh
$ make x64
```

or if you are in a 32bit machine.


```sh
$ make ia32
```

<br>

### What to do now ?

You can now execute the V8 REPL and load Javascript files, do profiling, and tons of other stuff. To had global access just add the binary to the system vars.

```sh
$ export $PATH:/home/cesar/v8/out/x64.release/d8
```

Or, what I found more interesting is use VM inside native programs and learn how to take advantage of a high level language like Javascript and give it some new abilities like Socket, Disk, etc. [Here] you can find a basic Hello World C++ program that run Javascript inside just need to clone it and start hack.


For those interested in how the VM works some useful links:

- [how it work inside]
- [nice Blog, the author write about v8 intrinsics]
- [Unofficial V8 API]



[how it work inside]: <https://docs.google.com/document/d/1hOaE7vbwdLLXWj3C8hTnnkpE0qSa2P--dtDvwXXEeD0/pub>
[nice blog, the author write about v8 intrinsics]: <http://wingolog.org/tags/v8>
[Unofficial V8 API]: <http://v8.paulfryzel.com/docs/master/>
[Here]: <https://github.com/cesarvr/v8-hacking>
[great talk]: <https://www.youtube.com/watch?v=UJPdhx5zTaw>
