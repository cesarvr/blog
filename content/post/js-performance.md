---
title: "Finding Performance Bottlenecks in JavaScript."
date: 2018-09-06T15:23:40+01:00
lastmod: 2018-09-06T15:23:40+01:00
draft: false
keywords: []
description: "How to use the Chrome performance monitor to optimise JavaScript performance."
tags: [Performance]
images:
  - https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/static/logo/js.png

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

One of my hobbies is to write (and sometimes re-write) graphic libraries in various languages. I like to do this because, for one thing I like to see cool animation flying on the screen and nice side effect is that when your code is not performant the animation on the screen will let you know, as simple as that if you write good enough code you will receive a quick feedback.


<!--more-->

To test my library I wrote a small animation that draw 1600+ particles and in each frame I update speed and angle to get a vortex like effect, then I repeat this every 33 millisecond (ms) and if the code is good enough it will look like this:

[Edge](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/js-performance/vortex-edge.gif)



**Chrome**
==================
![Chrome](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/js-performance/vortex-chrome.gif)





```js
    particles.forEach(particle => {
      //update particles

    })

    particles.forEach(particle => {
      //render the particles
    })
```

I take a quick look at what at this loops and I got the impression that the problem has to do with the utilisation of ```forEach``` instead of using a classic for from C. This would sound silly but my rationale that for each iteration a memory scope was being created and that that was messing with the speed of my animation.

With that assumption I edited my code.  

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

Now there is more code and less syntactic sugar but it looked C like and was giving me the impression that maybe should be faster. But I run the code again and I got 10 FPS and I was like "where are my other 50 frames?".

Now the code not only was slow but look uglier, this is what happen when you use the ["drunken man anti-method"](http://www.brendangregg.com/methodology.html).


# Solving The Mystery

Ironically Chrome has one of the best tools to instrument JavaScript applications and after this humbling experience, I decided that maybe I should give it a try, so I run the profiler and got this:

![debugger-chrome](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/js-performance/debugger-chrome.gif)

My first surprise is to see how much the profiler has improved, I'm able to see the correlation between the frames, time and instructions executed. After watching that I discover how much I wasted my time.

![profiler](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/js-performance/profiling.PNG)

To hunt the bottleneck I just need to look for functions that are beyond the ``33ms`` threshold, the profiler has facilitated this task by painting in yellow the spots that are lagging the most.

To look for a more detailed view I used the *Call Tree* section.

![data](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/js-performance/data!!.PNG)

The performance problem was calling *gl.getError()* inside the ```paint``` function, in Chrome.

```js
paint(object) {
  /*
     loading particles into WebGL 3.3ms
  */
  gl.getError() // 119.8ms  
}

```

That method ``gl.getError()`` logs to the console any exception that happens on WebGL and for some reason calling this function is very slow (**≈119ms**) on Chrome, even when I run my demo with the inspector closed while other browsers like Edge seems to deactivate that logging mechanism.

I rolled back those ugly changes and run the code again, [the demo now runs](http://webgl-hello01.7e14.starter-us-west-2.openshiftapps.com/gl_point/) at 60 FPS across all browsers (Android included).

### Always measure

The main problem was a mix of preconceived and laziness and as Michael Abrash put it his book the [Graphic Programming Black Book](http://www.jagregory.com/abrash-black-book/#understanding-high-performance).

> Assume nothing... If you don’t measure performance, you’re just guessing, and if you’re guessing, you’re not very likely to write top-notch code.


If you want to take a look at the source code, the project is published in [Github](https://github.com/cesarvr/vortex/tree/gl_point).    
