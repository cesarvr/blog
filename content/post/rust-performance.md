---
title: "Performance Showdown: Rust vs Javascript"
date: 2020-01-01T19:24:19+01:00
draft: false
keywords: []
description: "After spending some weeks playing with Rust, I felt ready to test my skills and try some programming challenges in the [Advent Of Code](https://adventofcode.com/). My approach to tackle some of those challenges was to solve them on Javascript first (I use it in my day to day) to then port the code to Rust, while porting I just focus on getting the Rust code as elegant as possible. It was after finishing porting this [puzzle](https://adventofcode.com/2018/day/5) in particular and feeling a sense of accomplishment that I decided to test how the Rust compiled code will perform against Javascript interpreter. "
images:
  - https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
categories: [OpenShift, BuildConfig]
tags: [Performance]
---

After spending some weeks playing with Rust, I felt ready to test my skills and try some programming challenges in the [Advent Of Code](https://adventofcode.com/). My approach to tackle some of those challenges was to solve them on Javascript first (I use it in my day to day) to then port the code to Rust, while porting I just focus on getting the Rust code as elegant as possible. It was after finishing porting this [puzzle](https://adventofcode.com/2018/day/5) in particular and feeling a sense of accomplishment that I decided to test how the Rust compiled code will perform against Javascript interpreter.  


## Naive Algorithm
----

Before jumping to the whom-was-slower-and-why, let’s take a quick look at [puzzle](https://adventofcode.com/2018/day/5) (so you see there is no hidden agenda) which goes like this: 

You are given an input string with ``N`` amount of characters and we should write an algorithm that find and remove any sequential pairs of characters that similar but have different capitalisation, examples of this are:

```sh
bB # Remove
bb # Do Nothing
ab # Do Nothing
```

The algorithm should re-evaluate the string recursively searching for new pairs created after the removal, something like tetris.

We have this input: 

```sh
# remove bB 
tdabBADp
```

We should remove ``bB`` to get:

```sh
# remove aA
tdaADp

```
Then because ``aA`` has been formed we should eliminated this too:

```sh
# remove dD
tdDp
```

Then we remove ``dD`` and the final string should be:

```sh
tp
```

### My Solution

To solve this I wrote two functions, one that ``process`` an array of strings and fetch a pair each time: 

#### Rust
----- 

```rust
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


#### Javascript
----- 

```js
function process(data) {
  let queue = []  // Save here tested characters.

  while(data.length > 0) {
    let candidate_1 = data.pop()
    let candidate_2 = queue.pop() // get the last character that passed the test. 

    if (candidate_2 === undefined) {
      queue.push(candidate_1)
      continue
    }

    let react = reacting(candidate_1, candidate_2)

    if(!react) {
      queue.push(candidate_2)
      queue.push(candidate_1)
    }
  }

  return result.length
}

```

> *Notice* the *performance* optimization by keeping the last character in a different queue, that way we don’t need to traverse the whole array looking for matches after a previous removal.


Then each pair of characters is evaluated using a function called ``react`` that returns ``true`` or ``false`` if the pair need to be removed:

#### Rust
----- 

```rust

  fn react(token1: &String, token2: &String) -> bool {
    if token1.to_lowercase() == token2.to_lowercase() {
        return token1 != token2
    }

    false
  }
```

#### Javascript
----- 

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

> Basically is a rudimentary implementation of a **equals-ignore-case** plus an additional check to see if they are they same character (the same capitalization).

To complete the challenge each version (Rust, Javascript) need to reduce a large string ([50K character](https://adventofcode.com/2018/day/5/input)) which is good enough to test how well one version performs against the other, then I run each code using Linux ``time`` and got this: 

```python
# Javascript (Node.js)
  real  0m0.374s
  user  0m0.301s
  sys   0m0.030s

# Rust
  real  0m0.720s
  user  0m0.636s
  sys   0m0.012s
``` 


Now that was unexpected, my first instinctive reaction was to make I was using the correct flag ``release`` and ``opt-level=3``, but even if that’s the case this (Rust code) was running natively and this language is supposed to be C++ level of fast. So I started to search for inefficiencies in the code using the ancient [Drunk man anti-method](http://www.brendangregg.com/methodology.html) technique which obviously didn’t work, so I settled for the sane approach of running the code through a profiler called [perf](https://perf.wiki.kernel.org/index.php/Main_Page). 



## Debugging
----

Every time you are debugging a performance issues you might feel tempted to start adding your own function to calculate the duration of suspicious section of code (like I used to do, in the past). [Perf](http://www.brendangregg.com/perf.html) does this for you by taking various approaches such as listening CPU/Kernel [performance events](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/6/html/developer_guide/perf) while your process is running. This makes perf the tool of choice to debug performance issues. Let’s see how it works. 


### Debugging Symbols

Before we start we need to enable the [debugging symbols](http://carol-nichols.com/2015/12/09/rust-profiling-on-osx-cpu-time/) on the Rust compiler, this will make ``perf`` reports more informative. To enable this just add ``debug=true`` to the ``Cargo.toml``:

```toml
[profile.release]
opt-level = 3
debug=true
```

### Attaching Perf

I recompiled the code and attached ``perf``: 

```zsh
cargo build
./target/release/day-5 & perf record -F 99 -p `pgrep day-5`
``` 

- First we run the Rust program (``day-5``) and we send it to the background using the ampersand (``&``) symbol. 
- Next to it, so it executes immediately, we run ``perf`` that receives the process identifier ([PID](https://en.wikipedia.org/wiki/Process_identifier)) courtesy of ``pgrep day-5``. 
- The [pgrep](https://linux.die.net/man/1/pgrep) command returns the [PID](https://en.wikipedia.org/wiki/Process_identifier) of a process by name.

Here is the output: 

```bash
[1] 27466
sample size 50003
--
solution 1: 9526
solution 2: 6694


[ perf record: Woken up 1 times to write data ]
[1]  + 27466 done       ./target/release/day-5
[ perf record: Captured and wrote 0.002 MB perf.data (13 samples) ]
```

### Report

After running this multiple times,``perf`` automatically aggregates the data to a report file  (``perf.data``) in the same folder where we are making the call. 

Now we can visualise the report with:

```sh
perf report
```

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/rust/perf-1.png)

Interestingly the algorithm spend **30 percent** of the time in the [String::to_lowercase](https://doc.rust-lang.org/std/string/struct.String.html#method.to_lowercase) which is suspicious:


```rust
fn react(token1: &String, token2: &String) -> bool {
    if token1.to_lowercase() == token2.to_lowercase() {  // 30% CPU wasted here
        return token1 != token2
    }

    false
}
```


My first impression is that I made a mistake while running ``perf`` (never used it before with Rust), but everything started to make sense once I looked at the source code of the [to_lowercase](https://doc.rust-lang.org/std/string/struct.String.html#method.to_lowercase) function.

What happen is that Rust lowercase function try to be correct in any language, so it delegates this conversion to a function called [std_unicode::conversions](https://doc.rust-lang.org/1.29.2/std_unicode/conversions/fn.to_lower.html) this function then does a [binary search](https://en.wikipedia.org/wiki/Binary_search_algorithm) of each character against a big array (≈1200) of unicode characters: 

```rust

const to_lowercase_table: &[(char, [char; 3])] = &[
        ('\u{41}', ['\u{61}', '\0', '\0']), 
        ('\u{42}', ['\u{62}', '\0', '\0']), 
        ('\u{43}',//...≈1200 ]


 pub fn to_lower(c: char) -> [char; 3] {
        match bsearch_case_table(c, to_lowercase_table) {
            None        => [c, '\0', '\0'],
            Some(index) => to_lowercase_table[index].1,
        }
    }

```

> Going back at the code, this binary search is done twice per iteration now multiply this by ``50K`` and we found the reason for the slow down. 


After some googling I found that I should use [eq_ignore_ascii_case](https://doc.rust-lang.org/src/core/str/mod.rs.html#4006) instead, which basically makes this operation on [linear time](https://doc.rust-lang.org/1.37.0/src/core/slice/mod.rs.html#2487) and for one character is nearly the same as saying constant time. I recompiled the code and run the benchmarks:

```xml
Node.JS
real  0m0.374s
user  0m0.301s
sys   0m0.030s

Rust
real  0m0.283s
user  0m0.248s
sys   0m0.005s
```

Now we are talking, profiling have pay its dividends and made the Rust program ``2.5x`` *faster* than the original and ``91ms`` faster than the Javascript version, I can start celebrating and telling my friends that I’m a **rustacean** now.

## Performance On MacOS

Thing is that I thought this was over, so while I was unpacking my Rust stickers and preparing my laptop for some re-branding, I decided to move the code (Javascript and Rust) from my Linux VM to my main OS (**MacOS Catalina**), once there I gave the benchmark another try because I *love* suffering:

```sh
Node   0.17s user 0.03s system 101% cpu 0.209 total
Rust   0.23s user 0.01s system 98% cpu 0.238 total
 ```

After seeing this I started to blame MacOS ``time`` implementation, but then I calm down and decided to profile the code again this time using [XCode Instrumentation](https://developer.apple.com/library/archive/documentation/AnalysisTools/Conceptual/instruments_help-collection/Chapter/Chapter.html) which point me in the right direction: 

![](https://github.com/cesarvr/hugo-blog/blob/master/static/rust/malloc-xcode-2.png?raw=true)

> The slowest part of the program is the part that does the allocation and deallocation of memory produced when calling MacOS ``malloc``. 

To catch this one I'll need to dig more into Rust inner workings. Does this make it more expensive to get performance out of Rust? Did I choose the wrong abstractions? That's for another post. If you want to take a look at the code yourself here is the [Rust](https://github.com/cesarvr/AOCRust/tree/master/day-5) and [JS](https://github.com/cesarvr/AOCRust/tree/master/JS), if you have any improvement, idea, suggestions or performance trick let me know by [Twitter](https://twitter.com/cvaldezr), [pull request](https://github.com/cesarvr/AOCRust) or [open an issue](https://github.com/cesarvr/hugo-blog/issues).

