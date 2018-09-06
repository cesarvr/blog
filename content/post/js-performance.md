---
title: "Writing High Performance Applications in JavaScript."
date: 2018-09-06T15:23:40+01:00
lastmod: 2018-09-06T15:23:40+01:00
draft: true
keywords: []
description: ""
tags: [JavaScript, Chrome, Performance]
categories: []
author: ""

# You can also close(false) or open(true) something for this content.
# P.S. comment can only be closed
comment: false
toc: false
autoCollapseToc: false
# You can also define another contentCopyright. e.g. contentCopyright: "This is another copyright."
contentCopyright: false
reward: false
mathjax: false
---

One of my hobbies is to write (and sometimes re-write) my graphics engine as an excuse to learn computer graphics techniques and OpenGL. This time I decide to write one in JavaScript using WebGL and as soon as I have a workable set of API's I decide to write an simple vortex animation to see how well my new shinny new engine will perform.  

<!--more-->

I run this demo using Chrome and to my surprise, I got 9 frames per seconds (FPS), that speed almost broke my spirit. But, out of curiosity I tried the demo in Firefox.62 and guess what? I got a solid 60 FPS, cool, now my moral was at level again but I wanted to tested with other browser and I run it in Edge and got the same speed 60 FPS rock solid, now this is curious.

**Microsoft Edge**
==================

![Edge](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/js-performance/vortex-edge.gif)

**Chrome**
==================
![Chrome](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/js-performance/vortex-chrome.gif)

My first thought was to blame the Chrome desktop browser, I checked Chrome in Android, in the hope that maybe by some kind of miracle my desktop version has some bug. I got even worst results with just 7 FPS. If want to share this demos with everybody I better solve this problem.

For that animation I create the total of 1600 particles and I try to update each particle with different speed and angle to get this vortex like effect. My first suspect was the loops in charge of animation and rendering in the update loop I handle I read the actual position, calculate a new position and update the particle. The second loop just go through all the particle and renders it to the screen. The code looks something like this:


```js
    particles.forEach(particle => updateParticle)

    particles.forEach(particle => render)
```

I check the code and I got the impression that the problem has to be the utilisation of ```forEach``` instead of using a classic for from C. I know it may sounds silly but I didn't have any other way (at that moment) to explain why my code was running fast in 2 of 3 browsers, I thought maybe I need something more "close to the metal" at least in appearance. So I change that with this implementation.

```sh

  for(let i=0; i<particles.length; i++) {
    let particle = particles[i]
    // update...
  }


  for(let i=0; i<particles.length; i++) {
    let particle = particles[i]
    // render...
  }

  //....
```

Now the code looks more verbose and less elegant but more C like and was giving me the impression that maybe should be faster. But I run the code again and I got 10 FPS. Which means that the code not only is slow but now I added a new problem of code ugliness. This is what happen when we take decision without proper information, you end up adding more problems.


# Solving The Mystery

Ironically Chrome has one of the best tools (in my opinion) to instrument JavaScript applications, after that failure I recognised I need some help and decide to give the Chrome profiler a chance.

Chrome profiler up and running:

![debugger-chrome](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/js-performance/debugger-chrome.gif)

My first surprise is to see how much the profiler has improved, I'm able to see the correlation between the frames, time and instructions executed.

![profiler](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/js-performance/profiling.PNG)

Before looking this graph just keep in mind that to perceive an animation as fluid (30 FPS) our program need to generate a new frame every 33ms which mean that to hunt the bottleneck I just need to look for the functions that are beyond that threshold. The code with the highest threshold is painted in yellow, but it gives you a global view, to get more details i have to go to the  *Call Tree* section.

![data](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/js-performance/data!!.PNG)



The problem at the end was *gl.getError()* inside the ```paint``` function.

```js
paint(object) {
  /*
     bindBuffer... 3.3ms
  */
  gl.getError() // 119.8ms  
}

```

That method logs to the console any exception that happens in that blackbox of WebGL and for some reason calling this function is very slow (≈119ms) in Chrome, even when I run my demo with the inspector closed. Other browsers are behaving more intelligently and are deactivating this mechanism if the inspector is closed.

I rollback those ugly changes and run the code again, [the demo now runs](http://webgl-hello01.7e14.starter-us-west-2.openshiftapps.com/gl_point/) at 60 FPS across all browsers (Android included). The main problem here was assuming I can solve that problem without measuring and doing that is just wasting time and energy. As Michael Abrash put it in that great book, [Graphic Programming Black Book](http://www.jagregory.com/abrash-black-book/#understanding-high-performance).

> Assume nothing... If you don’t measure performance, you’re just guessing, and if you’re guessing, you’re not very likely to write top-notch code.    
