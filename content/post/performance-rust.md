---
title: "Performance Profiling in Rust"
date: 2019-08-07
draft: false
keywords: []
description: "Writing performant Rust code."
tags: [Programming, Performance]
toc: true
image: https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
draft: true
---

I had the impression that Rust being a system language its performance should be comparable only to C/C++, that the worst code in Rust should perform faster than the good code written in a high level language like JavaScript. Well I discover by pure accident that that's not always the case. It all started when I tried to benchmark an algorithm that I wrote to solve a puzzle and I found out for my surprise that my JS code was performing twice as fast than my Rust implementation.

The critical part of the algorithm was to create a function that accept two characters as parameters and return ``true`` if the characters are equal but they have a different capitalisation.

For example:

```sh
'aA'
'bB'
'Cc'
```

My Rust implementation look like this:

```js
fn react(token1: &String, token2: &String) -> bool {
    // Are they equals ignoring the case.
    if token1.to_lowercase() == token2.to_lowercase() {
        // are they still equals ?
        return token1 != token2
    }

    false // if they don't match we just move on.
}
```

> My C instincts are telling me that this looks efficient.

The code in JavaScript looks very similar:

```js
function react(candidate_1, candidate_2) {
  if (candidate_1.toLowerCase() === candidate_2.toLowerCase()) {
    if ( candidate_1 !== candidate_2 ) {
      return true
    }
  }

  return false
}
```

> More verbose than Rust, for sure.


# Performance

In one corner Rust uses the LLVM backend to generate machine code, while Javascript in the other corner is an **interpreter** that does some black magic transform hot parts of the code into machine code, so this should be a walk in the park for Rust.

### Benchmark

This puzzle has an input of [50K characters](https://raw.githubusercontent.com/cesarvr/AOCRust/master/day-5/input.txt) and this where the result:

```xml
Node.JS
  real	0m0.374s
  user	0m0.301s
  sys	0m0.030s

Rust
  real	0m0.720s
  user	0m0.636s
  sys  	0m0.012s
```
> This broke my heart, my Rust algorithm is twice slower than Javascript.

![](https://media.giphy.com/media/2wSaulb0fsDydh0IoB/giphy.gif)

My first reaction was to do what serious *Senior Software Engineer* would do, I ask Google for Rust compiler optimisation options. The search came up with a [good article](http://carol-nichols.com/2015/12/09/rust-profiling-on-osx-cpu-time/) on how to pass flags to the compiler.

I added the optimisation flag to the ``Cargo.toml`` and run the benchmark again.

```toml
[package]
name = "day-5-puzzle"
version = "0.1.0"
authors = ["cesar"]
edition = "2018"

[dependencies]

[profile.release]
opt-level = 3
```

After I did this, I recompile and run the benchmarks one more time:

```sh
Node.JS
  real	0m0.374s
  user	0m0.301s
  sys	0m0.030s

Rust  
  real	0m0.723s
  user	0m0.642s
  sys  	0m0.010s
```

> Now is even worst...

It was clear that some piece of code is or pattern is killing performance, so after a few hours applying the ["Drunk Man Anti-Method"](http://www.brendangregg.com/methodology.html) techniques to my Rust code, I started to consider that maybe the best way to find out the problem was to profile the code using [Linux perf](https://perf.wiki.kernel.org/index.php/Main_Page), the problem was that I wasn't sure that it would work very well with Rust.

#### Install

For those who never hear before about [perf](https://perf.wiki.kernel.org/index.php/Main_Page), it's a powerful **Linux** tool to profile programs at runtime, to install it you can use your favourite package manager:

```sh
#install perf in Archlinux
sudo pacman -Sy perf

#install perf in Fedora
sudo dnf install perf

#ubuntu
sudo apt install linux-tools-common
```

#### Syntax

```sh
 perf record -F 99 -p `PID`
```

  - ``record`` it samples a process.
  - ``F`` You specify the sampling frequency ``99hz``.
  - ``p`` We need here the process identifier (PID).


#### Rust Debug Symbols

Enabling debugging symbols will make the [profiling](http://carol-nichols.com/2015/12/09/rust-profiling-on-osx-cpu-time/) experience more enjoyable by adding source code to the sampling.

 Adding ``debug`` property to ``Cargo.toml`` will enable it:

```toml
[profile.release]
opt-level = 3
debug=true
```

#### Profiling

Now we just need to execute the program and attach ``perf`` like this:

```sh
./target/release/day-5 & perf record -F 99 -p `pgrep day-5`

[1] 27466
sample size 50003
--
solution 1: 9526
solution 2: 6694
[ perf record: Woken up 1 times to write data ]
[1]  + 27466 done       ./target/release/day-5
[ perf record: Captured and wrote 0.002 MB perf.data (13 samples) ]
```

After sampling the process multiple times, we can visualise it:

```sh
perf report
```

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/rust/perf-1.png)

>  This simple old-school UI shows where our program is spending the CPU cycles.

Interestingly the program spend a lot of time in this area:

![Hotspot](https://github.com/cesarvr/hugo-blog/blob/master/static/rust/perf-hotspot.png?raw=true)

I didn't occur to me that [String::to_lowercase](https://doc.rust-lang.org/std/string/struct.String.html#method.to_lowercase) was so expensive and here is why:

```js
token1.to_lowercase() == token2.to_lowercase()
```
> Every time use [to_lowercase](https://doc.rust-lang.org/std/string/struct.String.html#method.to_lowercase) the code underneath does a binary search against a [UTF-8 lookup table](https://doc.rust-lang.org/1.29.2/src/core/unicode/tables.rs.html#1297) per each character in the string.

![](https://github.com/cesarvr/hugo-blog/blob/master/static/rust/call-stack.png?raw=true)


A faster alternative is to use [eq_ignore_ascii_case](https://doc.rust-lang.org/src/core/str/mod.rs.html#3961), this one operate with ASCII characters which make this operation almost constant time.

[After some replacement](https://github.com/cesarvr/AOCRust/compare/master...perf) I recompiled the program and run the benchmarks again:

```xml
Node.JS
real	0m0.374s
user	0m0.301s
sys	0m0.030s

Rust
real	0m0.283s
user	0m0.248s
sys	0m0.005s
```

![](https://media.giphy.com/media/W9WSk4tEU1aJW/giphy.gif)

> Now this looks better...

This simple change made the program 2.5x faster, now we are talking.

### Lessons Learned

This experiment make me think about the amount of time that we think on terms about speed like absolute metric, but we should take into consideration how resilient is a programming language running non-expert code. 

Well here are some take aways from this experience, if you want to choose a language assuming that is faster, you should take in account the time you are willing to spend optimising your first **naive algorithm** implementation. Of course as soon as you get more experience you will be able to hit the performance sweet spot.

Languages JS or Go seems to have a lower barrier in this regard and is something you should consider when choosing a language for a new project that may require good performance but not exceptional.

In the other hand if you need exceptional performance and you are willing to profile your program with discipline, then Rust the right choice in my opinion, not only give you speed but also provides you with a safety net of having a compiler helping (or annoying) you about common memory mistakes and vulnerabilities. No wonder [Dropbox use Rust](https://www.wired.com/2016/03/epic-story-dropboxs-exodus-amazon-cloud-empire/) for their distributed filesystem.

### Wrapping Up

Me personally I like to learn about low-level stuff in Linux and Rust helps to write programs that are close to the metal while keeping the illusion of high level.

Also I want to write another article because, if you run this algorithm on **MacOSX** I discover that my Rust implementation is again **slower** or on par with the runtimes languages **again**, take a look at this:

##### MacOSX

```sh
Rust      0.21s user 0.01s system 97% cpu 0.220 total
Node.js   0.17s user 0.08s system 61% cpu 0.409 total
Go        0.20s user 0.01s system 111% cpu 0.191 total
```

In my next post I'm going to talk about the causes for this **performance degradation**, how to use [Xcode Instruments](https://developer.apple.com/library/archive/documentation/AnalysisTools/Conceptual/instruments_help-collection/Chapter/Chapter.html) to profile Rust on MacOSX and explore if we can do something about it.

If you have any improvements on the algorithms above or any suggestion on how to make them faster [let me know](https://twitter.com/cvaldezr).
