---
title: "Rust Performance"
date: 2020-01-13T14:00:55Z
draft: false
---

I wanted to learn Rust programming language after having heard good things about it, so I decided to give it a try and to make the learning experience more enjoyable I learn by solving some of the challenges of [Advent Of Code 2018](https://adventofcode.com/). To solve some of these puzzles what I do is to model the solution in a language that I know like Javascript and when I have a working solution I port it to Rust.

Something interesting happened when I finished porting the [day 5](https://adventofcode.com/2018/day/5) challenge as I wanted to see how fast the Rust version will perform against Javascript interpreter. With this purpose I setup a quick benchmark where I used the provided puzzle input (a string with [50K characters](https://raw.githubusercontent.com/cesarvr/AOCRust/master/day-5/input.txt)) and used Linux ``time`` to measure time it takes to complete the task:

```sh
#Node.JS
  real	0m0.374s
  user	0m0.301s
  sys	 0m0.030s

#Rust
  real	0m0.720s
  user	0m0.636s
  sys     0m0.012s
```

To my surprise Javascript version was nearly twice as fast than the Rust version. **How can it be?** We are talking that Rust compiles to machine code, zero cost abstraction, no interpreter mode and no garbage collection. I started to wonder what could be the explanation for this so I took a quick look at the algorithm.

## Naive Algorithm

### Puzzle

The [day 5](https://adventofcode.com/2018/day/5) the puzzle involves having a string with ``N`` amount of characters, then I have to write an algorithm that find and remove each pairs of characters that are equals but have different capitalisation and then re-evaluate the string searching for new pairs created after the removal.

A quick example let say we get this input ``abBAp``:

I should remove ``bB`` to get:

```sh
aAp
```
And now ``aA`` has been formed and require to be removed as well:

```sh
# remove aA
p
```

With the final result of ``p``.

### Solution

To solve this I wrote two functions, one that **scan** the string fetching a pair each time, then I evaluate the pair using a function called **react** that returns true or false if the pair need to be removed.

Here is what the function looks like in Rust:

```rust
fn react(token1: String, token2: String) -> bool {
    if token1.to_lowercase() == token2.to_lowercase() {
        return token1 != token2
    }

    false
}
```
> Basically is a rudimentary implementation of a **equals-ignore-case** if true then it checks that the are the same character.  

Here is what the function looks like in JS:

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

As you can see they both look very similar, there is nothing fancy here so I expect each language to perform normally but that wasn't the case with Rust, so after a few hours of me applying the ["Drunk Man Anti-Method"](http://www.brendangregg.com/methodology.html) which consist in my wasting my time making changes to the code here and there in the false believe that I know what I'm doing, I decided to profile the code.

## Profiling

For those who never hear before about [perf](https://perf.wiki.kernel.org/index.php/Main_Page), it's a powerful **Linux** tool to profile processes on Linux, here is some installing instructions:

```sh
#install perf in Archlinux
sudo pacman -Sy perf

#install perf in Fedora
sudo dnf install perf

#ubuntu
sudo apt install linux-tools-common
```

Here is the syntax:

```sh
 perf record -F 99 -p `PID`
```

  - ``record`` it samples a process.
  - ``F`` You specify the sampling frequency ``99hz``.
  - ``p`` We need here the process identifier (PID).

[For more information...](http://man7.org/linux/man-pages/man1/perf.1.html)

### Getting Started

Before I can start profiling my Rust program I've to tell the compiler to add [debugging symbols](http://carol-nichols.com/2015/12/09/rust-profiling-on-osx-cpu-time/), this will make things easier later. We can enable it by adding the ``debug`` property to the ``Cargo.toml`` configuration file:

```toml
[profile.release]
opt-level = 3
debug=true
```
### Perf In Action

Then I executed the benchmark again and attached ``perf`` like this:

```sh
./target/release/day-5 & perf record -F 99 -p `pgrep day-5`
```
Here we run the ``day-5`` process using the ``&`` symbol, so it runs in the background. Just after that ampersand I run ``perf`` which receives the process id (``PID``) courtesy of ``pgrep``, which returns the ``PID`` of a process by name, in this case ``day-5``.

```sh
[1] 27466
sample size 50003
--
solution 1: 9526
solution 2: 6694
[ perf record: Woken up 1 times to write data ]
[1]  + 27466 done       ./target/release/day-5
[ perf record: Captured and wrote 0.002 MB perf.data (13 samples) ]
```

I run this multiple times and while doing this ``perf`` creates a report called ``perf.data``, then visualise this report then I use:

```sh
perf report
```

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/rust/perf-1.png)

Interestingly the algorithm spend **30 percent** of the time in the [String::to_lowercase](https://doc.rust-lang.org/std/string/struct.String.html#method.to_lowercase) function bottlenecking the whole process:

```Rust
if token1.to_lowercase() == token2.to_lowercase()
```
To be honest this was the last place I was expecting to see a performance problem and that’s why profiling is a good practice after all, using this as an starting point I started to look at the Rust documentation for the [to_lowercase](https://doc.rust-lang.org/std/string/struct.String.html#method.to_lowercase) function and by looking a the source code I found that ever time my naive algorithm calls [to_lowercase](https://doc.rust-lang.org/std/string/struct.String.html#method.to_lowercase) this function is doing a binary search against a [UTF-8 lookup table](https://doc.rust-lang.org/1.29.2/src/core/unicode/tables.rs.html#1297) ending my aspirations to beat my JS algorithm.

![](https://github.com/cesarvr/hugo-blog/blob/master/static/rust/call-stack.png?raw=true)

After some more googling I found that I should use [eq_ignore_ascii_case](https://doc.rust-lang.org/src/core/str/mod.rs.html#4006) which basically makes this operation [linear time](https://doc.rust-lang.org/1.37.0/src/core/slice/mod.rs.html#2487) and for one character is nearly the same as saying constant time.

[After some refactoring](https://github.com/cesarvr/AOCRust/compare/master...perf) I recompiled the code and run the benchmarks again:

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

Now we are talking, my research pay its dividends and made the Rust program 2.5x faster than the original and ``75%`` faster than the Javascript version I can start celebrating.

## Rust vs Go

After this experience I wanted to see how other system programming language handle this naive algorithm. To test this I a ported the code to Go which I'm not an expert either and run it against my now *optimised* Rust.

Here is a quick example of the *equal-ignore-case* function in Go:

```go
func React(a, b string) bool {
  if strings.ToLower(a) == strings.ToLower(b) {
    return a != b
  }

  return false
}
```

And the here is some benchmarks:

```xml
Go
real	0m0.174s
user	0m0.172s
sys	 0m0.017s

Rust  
real	0m0.157s
user	0m0.127s
sys     0m0.014s
```

One quick observation here is that this Rust version is even lower than before because I optimised the code further by removing the copying of variable to passing by reference (``&``) in the functions parameters:

```Rust
// from  -> fn react(token1: String, token2: String)
// To this
fn react(token1: &String, token2: &String)
```

One thing I got from this experience is that yes Rust at the end is more performant but it can require a good amount of time to hit the performance sweet spot. Of course this was a very particular case and maybe in other cases performance gains can be obtain out of the box, but I will take this as a remainder to always benchmark the code.



### Wrapping Up

But what happen if you run this algorithm on **MacOSX** I discover that my Rust implementation is again **slower** or on par with the runtimes languages, take a look at this:

```sh
Rust      0.23s user 0.01s system 98% cpu 0.238 total
Node      0.19s user 0.03s system 101% cpu 0.209 total
Go        0.20s user 0.01s system 111% cpu 0.191 total
```

Its same *optimised* algorithm but it performed worse on MacOSX than in Linux. In my next post I'm going to talk about the causes for this **performance degradation**, how to use [Xcode Instruments](https://developer.apple.com/library/archive/documentation/AnalysisTools/Conceptual/instruments_help-collection/Chapter/Chapter.html) to profile Rust on MacOSX and explore if we can do something about it.
