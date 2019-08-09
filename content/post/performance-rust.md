---
title: "Performance Profiling in Rust"
date: 2019-08-07
draft: false
keywords: []
description: "Writing performant Rust code."
tags: [Rust, Programming, Performance]
toc: true
image: https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
---


One of my objectives this year is to learn Rust and Go, to make the learning process less boring I decided to solve the challenges of the [Advent Of Code 2018](https://adventofcode.com/) website, they are like 25 challenges and I try to write an algorithm and implement it in both languages.

Just for curiosity I wanted to see how well one language is against the other in the performance area, so I decide to run a quick test and the results where very surprising.

# Puzzle
----------------

Let's start by defining the problem, it all started when I tried to solve this [Day-5 Challenge](https://adventofcode.com/2018/day/5), which is a puzzle that has two parts, and it goes like this:

#### First Part


* **Given an input** in the form of a string:

```sh
'dabAcCaCBAcCcaDA'
```

* Look inside the string for a pair of a ``chars`` that are equals but has different capitalisation (for example ``aA``, ``cC`` , ``dD``, etc.) and **remove any match** from the string, for example:

```sh
dabA'cC'aCBAcCcaDA  The first 'cC' is removed.
dab'Aa'CBAcCcaDA    This creates 'Aa', which is removed.
dabCBA'cCc'aDA      Either 'cC' or 'Cc' are removed (the result is the same).
dabCBAcaDA          No further actions can be taken.
```

* It also need to be recurrent, for example:

```sh
oaDdAo => oa'Dd'ao => oaao => o'aa'o => 'oo' => ""
```

* Then I just need to return the size of the final state of the string in the case above the answer is ``10``.

----------------
#### Second Part

In the **second part** you need to do some pre-process to the **given string**, by removing all matching characters of a particular type, before running the algorithm:

```sh
'dabAcCaCBAcCcaDA'

```

* We got ``abcd`` as unique characters, so we can generate 4 different arrays this way:

```sh
Given: 'dabAcCaCBAcCcaDA'

Removing all A/a 'dbcCCBcCcD' => applying algorithm above produce 'dbCBcD' length 6.
Removing all B/b 'daAcCaCAcCcaDA'. => 'daCAcaDA' length 8.
Removing all C/c 'dabAaBAaDA' => 'daDA' length 4.
Removing all D/d 'abAcCaCBAcCcaA' => 'abCBAc' length 6.
```

* Then we apply the algorithm to each transformation and choose the one with minimum size:

```sh
'dabAcCaCBAcCcaDA' => [[...],[...],[...],[...]] => [6,8,4,6]
```

* The correct answer is ``4``.


As mentioned before I'm learning Rust so I don't expect it to be perfect, but that also count for my Go version, so let's write some code.

### Writing Some Code
---------------
##### Part One
To solve the first part of the puzzle I divided the problem in two functions:

- First function is called ``react``, it evaluates a pair of letter to see if they match the ``a/A`` we saw before pattern:

```js
fn react(token1: &String, token2: &String) -> bool {
    // Are they equals ignoring the case.
    if token1.to_lowercase() == token2.to_lowercase() {  
        // are they still equals ?
        return token1.to_string() != token2.to_string()
    }

    false // if they don't match we just move on.
}
```

The second function ``process``, scan a collection of strings:

```js
fn process(tokens: &mut Vec<String>) -> i32 {
    let mut polymer: Vec<String> = Vec::new();

    while let Some(token) = tokens.pop() {
        if polymer.is_empty() {
            polymer.push(token);
            continue;
        }

        let candidate = polymer.pop().unwrap();

        if !react(&candidate, &token) {
            polymer.push(candidate.to_string());
            polymer.push(token.to_string());
        }
    }

    polymer.len() as i32
}
```

It receives a mutable [vec::Vec](https://doc.rust-lang.org/std/vec/struct.Vec.html) collection and treat it like a queue, retrieving a pair of number from the back of the collection.

Then I check the pair of characters using the function ``react`` from above and if they don't *react* they are inserted into the ``polymer`` collection. In next iteration I retrieve one character from the back of both collections, compare and continue until the ``tokens`` collection ran out of elements.

Finally the function returns the size of the ``polymer`` collection which has the final state (reversed) of a fully ``reacted`` string.


![](https://github.com/cesarvr/hugo-blog/blob/master/static/rust/first_puzzle.png?raw=true)

 > This function gets a Collections returns a number representing the final state of the string after apply the algorithm.



##### Part Two

I wrote one more function called ``remove_unit``:

```js
fn remove_unit(polymer: &Vec<String>, remove_chr: &str ) -> Vec<String> {
    let mut npoly: Vec<String> = polymer.to_vec();

    npoly.retain(|s|
      *s != remove_chr.to_lowercase() &&
      *s != remove_chr.to_uppercase() );

    npoly
}
```

* It takes a collection, makes a copy, removes from the copy any character that match ``remove_chr``, using the [std::vec::Vec::retain](https://doc.rust-lang.org/std/vec/struct.Vec.html#method.retain) and returns the new collection.


Then I wrote this block of code that maps each character of the **given string** against the combined effect of ``remove_unit`` and ``process``, generating a collection of solutions.

```js
let mut cache : HashMap<String, bool> = HashMap::new();

 let minimum_reaction = code.iter().map(|chr| {
    if None == cache.get(&chr.to_lowercase()) {
        let mut moded = remove_unit(&code, chr.as_str());

        cache.insert(chr.to_lowercase(), true);
        return process(&mut moded);
    }
    0x00beef
}).filter(|&n| n != 0x00beef)
  .min()
  .unwrap();

println!("solution 1: {}", process(&mut code.to_vec()) );
println!("solution 2: {}", minimum_reaction);

```

> Also I implemented cache using a HashMap so we don't process characters we have seen before.

![](https://github.com/cesarvr/hugo-blog/blob/master/static/rust/design.png?raw=true)

> Visualization of the algorithm.


At the end of this mapping we obtain an array with the solutions and to solve the second part I just need to filter this array to get rid of the cache hits (``0x00beef``) and get just smallest number (``min``).  

```sh
code_block('dabAcCaCBAcCcaDA') => [6,8,4,6] => [4]
```

Then I just get the minimum number from there and solve the puzzle.

Not bad at all for few weeks of fighting the *pedantic* Rust compiler, but I feel good with the result so far.


# Performance

The general assumption is that Rust should be faster than higher level languages like Javascript. Rust uses the LLVM backend to generate machine code, while Javascript is a **virtual machine interpreter** reading, executing code and then using some black magic to optimise code at runtime.

With that in mind I decided to run some benchmark using [time](https://linux.die.net/man/1/time) command, just to confirm my preconceived ideas.

### Benchmark

As I mentioned at the start of the post I also wrote another implementation of this [algorithm in GO](https://gist.github.com/cesarvr/cc9a62acc5dfad67f46733c40ba4f4f6), for learning purposes and to make this test interesting I wrote also a [JS version](https://gist.github.com/cesarvr/b0b7826f614d9d3250563ec6d7c2abcc).

This challenge came with a input string of [50K characters](https://raw.githubusercontent.com/cesarvr/AOCRust/master/day-5/input.txt) that need to be processed and the website also validates the correct solution, which is handy to check the correctness of the code in the three languages.

Here are some benchmarks:

```xml
Node.JS
  real	0m0.374s
  user	0m0.301s
  sys	0m0.030s

Go
  real	0m0.299s
  user	0m0.295s
  sys	0m0.038s

Rust
  real	0m0.720s
  user	0m0.636s
  sys  	0m0.012s
```
> This almost destroy my Rust aspirations.





The performance of my algorithm in Rust almost broke my heart, it's almost two times slower than JS and ``2.5`` slower than Go.

![](https://media.giphy.com/media/2wSaulb0fsDydh0IoB/giphy.gif)

This almost shatter my dreams of becoming a Rust hacker, but then I started to think that there has to be some explanation for this, remember one of this language (Rust) is running loose, no runtime, just machine instruction going to the CPU, how can we explain this ?.

## Debugging

My first reaction was to do what a *Senior Engineer* would do, which is make a Google search and see what can I found about Rust compiler optimisation. The search came up with a [good article](http://carol-nichols.com/2015/12/09/rust-profiling-on-osx-cpu-time/) on how to pass flags to the compiler which I did:

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

Just after that I run the benchmarks again and got this:

```sh
Node.JS
  real	0m0.374s
  user	0m0.301s
  sys	0m0.030s

Go
  real	0m0.299s
  user	0m0.295s
  sys	0m0.038s

Rust  
real	0m0.723s
user	0m0.642s
sys  	0m0.010s
```

> Now is even worst...

To be fair that has to do less with the flags, and more with the unavoidable fact that there is something unoptimisable inside the code. After blaming Rust for a few days I decide to *man up* and face the challenge of looking for the real reason of why my Rust code was performing worst than JS.

I started by performing the ["Drunk Man Anti-Method"](http://www.brendangregg.com/methodology.html) that involves changing random things and hope that that would solve my problem (which obviously didn't work),  so after that I decide to make my life easier and use [Linux performance tools](http://www.brendangregg.com/linuxperf.html).


## Linux Performance Tools

Moderns CPU's includes a set of registers that store CPU metrics events like instruction per seconds (IPC), cache-misses or branch miss predicted.

The fact that this counters are maintained at hardware level makes the chase of performance issues much more efficient, my only doubt was that if this is going to integrate well with Rust, which it does and we can see in a moment.


#### Perf

To read this information metric information per process we have to use a convenient tool called [perf](https://perf.wiki.kernel.org/index.php/Main_Page).

To install [perf](https://perf.wiki.kernel.org/index.php/Main_Page) we can use one of this options:

```sh
#install perf in Archlinux
sudo pacman -Sy perf

#install perf in Fedora
sudo dnf install perf

#ubuntu
sudo apt install linux-tools-common
```

#### Usage

Here is the quick syntax ``perf``:  

```sh
 perf record -F 99 -p `PID`
```
- ``F`` You specify the sampling frequency ``99hz``.
- ``p`` We need here the process identifier (PID).


#### Readability

My concerns of Rust integration with ``perf`` disappeared when I found how to enable [debugging symbols](http://carol-nichols.com/2015/12/09/rust-profiling-on-osx-cpu-time/), otherwise I will only see obscure x86 assembler instructions.

Adding ``debug`` to ``Cargo.toml`` will do the trick:

```toml
[profile.release]
opt-level = 3
debug=true
```

#### Profiling

I recompiled the code again:

```sh
 cargo build --release
```

Run the process (I call it ``./day-5``) and attach ``perf``:

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


> The ampersand ``&`` will make the two to start in parallel and luckily the process (``day-5``) lives long enough seconds to be sampled by ``perf``. To pass the process identification (PID) for the ``-p`` flag I used ``pgrep``.  



#### Fixing

After running it a few time to collect enough samples we have enough sample data to visualise the execution graph using ``perf report``:

```sh
perf report
```

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/rust/perf-1.png)

>  This simple old-school UI shows where our program is spending the CPU cycles.

Interesting the program spend a lot of time in this area:

![Hotspot](https://github.com/cesarvr/hugo-blog/blob/master/static/rust/perf-hotspot.png?raw=true)

And this is the reason of why measuring always beat the ["Drunk Man Anti-Method"](http://www.brendangregg.com/methodology.html), I would never be suspicious of this particular line.

Here is the problem:

![](https://github.com/cesarvr/hugo-blog/blob/master/static/rust/call-stack.png?raw=true)

Every the execution gets to [String::to_lowercase](https://doc.rust-lang.org/std/string/struct.String.html#method.to_lowercase) you end up performing a binary search against a [UTF-8 lookup table](https://doc.rust-lang.org/1.29.2/src/core/unicode/tables.rs.html#1297) per character, that operation is very expensive and if we do that 50K, well you saw the benchmarks.

Once I found this, it was obvious that Rust should offer and faster alternative and this was in the form of [eq_ignore_ascii_case](https://doc.rust-lang.org/src/core/str/mod.rs.html#3961), this one transform the bytes and compares by shifting the ASCII characters, which make each operation in constant time.

[I modified the parts](https://github.com/cesarvr/AOCRust/compare/master...perf) of the program that use [to_lowercase](https://doc.rust-lang.org/std/string/struct.String.html#method.to_lowercase) to use the fastest version instead and run the benchmarks again:

```xml
Node.JS
real	0m0.374s
user	0m0.301s
sys	0m0.030s

Go
real	0m0.299s
user	0m0.295s
sys	0m0.038s

Rust
real	0m0.283s
user	0m0.248s
sys	0m0.005s
```

![](https://media.giphy.com/media/W9WSk4tEU1aJW/giphy.gif)

> Now this looks better...

This simple change made the program 2.5x faster, now we are talking, after this moral boost I decided to push a bit more the envelope and run ``perf`` again to see what else can I improve in my code.

When I run it again I got the following:

![](https://github.com/cesarvr/hugo-blog/blob/master/static/rust/Screenshot%202019-08-07%20at%2021.26.42.png?raw=true)

Now the hot function is ``Clone``, telling me that a lot of copying of strings objects is going on, not making a good use of references I think, so I made a quick scan at the code and removed all the string copying.

![](https://github.com/cesarvr/hugo-blog/blob/master/static/rust/diff.png?raw=true)

Basically in my first attempt I abused to much of the [to_string()](https://doc.rust-lang.org/std/string/trait.ToString.html) function, so [I eliminate all unnecessary copy](https://github.com/cesarvr/AOCRust/compare/perf...perf-2?diff=split) and tried the benchmark again.


```xml
Node.JS
real	0m0.374s
user	0m0.301s
sys	0m0.030s

Go
real	0m0.299s
user	0m0.295s
sys	0m0.038s

Rust
real	0m0.207s
user	0m0.171s
sys	0m0.010s
```

> Now the algorithm is 3x faster, I can call me self Rust newbie.

### Lessons Learned

Well here are some take aways from this experience, if you want to choose a language assuming that is faster, you should take in account the time you are willing to spend optimizing your **naive algorithm** implementation, assuming you are not an expert.

Languages JS or Go seems to have a lower barrier in this regard and is something you should consider when choosing a language for a new project that may require good performance but not exceptional.

In the other hand if you need exceptional performance and you are willing to profile your program with discipline, then Rust cannot only give you take you there at almost the same level of C/C++, but it also provide you with the safety net of having a compiler helping (or annoying) you about your mistakes.

### Wrapping Up

Me personally I like low-level system and Rust brings a high level syntax to write really expressive algorithms. I'll continue learning it on my free time.

Also I want to write another article because, if you run this algorithm on **MacOSX** I discover that my Rust implementation is again **slower** or on par with the runtimes languages **again**, take a look at this:

##### MacOSX

```sh
Rust      0.21s user 0.01s system 97% cpu 0.220 total
Node.js   0.17s user 0.08s system 61% cpu 0.409 total
Go        0.20s user 0.01s system 111% cpu 0.191 total
```

In my next post I'm going to talk about why the **slowness** of this particular case, how to use instruments to get to the core of this and explore if we can do something about it.

If you have any improvements on the algorithms above or any suggestion on how to make them faster [let me know](https://twitter.com/cvaldezr).
