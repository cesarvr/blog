---
title: "Performance Showdown: Rust vs Javascript Round 2"
date: 2020-10-20T10:55:00+02:00
draft: false
---

A while ago I wrote a [blog post](https://cesarvr.io/post/rust-performance/) post about my learning adventure with Rust, to make thing interesting I was trying to use Rust to solve some [programming puzzle](https://adventofcode.com/2018/day/5) and by curiosity I decided to use this puzzle as a benchmark to measure what language was faster Rust or Javascript.

On paper the Rust implementation should win by a mile, surprisingly I found out that I was wrong so I started to profile the code looking for bottlenecks and found something interesting, I was using the [slowest function to turn characters to lowercase](https://cesarvr.io/post/rust-performance/), fixing this issue put things on par.

But that was on Linux, when I moved the code to MacOS I found out that the JS implementation was still performing faster there.


```sh
Node   0.17s user 0.03s system 101% cpu 0.209 total
Rust   0.23s user 0.01s system 98% cpu 0.238 total
```

Well time to do more profiling this time using [Instruments](https://help.apple.com/instruments/mac/current/) on MacOS, then looking at the samples I found the issue:  

![](https://github.com/cesarvr/hugo-blog/blob/master/static/rust/malloc-xcode-2.png?raw=true)

It seems that the Rust version is spending the majority of its time doing memory allocation triggered by a ``string:Clone`` method, this is what the Rust docs has to say about it:

> [[Clone]](https://doc.rust-lang.org/std/clone/trait.Clone.html) differs from Copy in that Copy is implicit and extremely inexpensive, while Clone is always explicit and may or may not be expensive...

Well it seems that I got the expensive part here, so I decided to [look for parts of my code](https://github.com/cesarvr/AOCRust/blob/master/day-5/first/src/main.rs) that might trigger a ``string::clone``, and one of those candidates was ``to_vec`` which the documentation defines as:

> Copies self into a new Vec.

Very economic definition, but is as mentioned before is not really a copy is a cloning, what happens behind the scene is this, when you call ``to_vec``,  first memory is allocated using [here](https://doc.rust-lang.org/beta/src/alloc/slice.rs.html#151) using the [boxed::Boxed](https://doc.rust-lang.org/std/boxed/struct.Box.html) function, which in turns triggers a [malloc](https://github.com/lattera/glibc/blob/master/malloc/malloc.c) which is a slow operation (on MacOSX in particular).

The only problem is that the code was very dependent on ``to_vec`` and I didn’t feel in the mood of starting a discussion with the [borrow checker](https://doc.rust-lang.org/1.8.0/book/references-and-borrowing.html) over how to move things around, so I decided to rewrite the code from scratch.  


```rust
use std::fs;
use std::cmp;
use std::collections::HashMap;

fn solve1(input: &str) -> usize {
    let mut reacts = Vec::new();

    for n in input.chars() {

        if reacts.is_empty() {
            reacts.push(n);
            continue;
        }

        if let Some(bn) = reacts.pop() {
            if bn.eq_ignore_ascii_case(&n) && bn != n {
                continue;
            }else{
                reacts.push(bn);
                reacts.push(n);
            }
        }
    }

    reacts.len() - 1
}

fn solve2(input: &str) -> u32 {
    let mut repeated = HashMap::new();
    let mut minimal: u32 = std::u32::MAX;

    for c in input.chars() {
        if None != repeated.get(&c.to_ascii_lowercase()){
            continue;
        }

        let batch = input.chars().filter(|n| {
            !c.eq_ignore_ascii_case(&n)
        });

        let solved = solve1(&batch.collect::<String>());
        minimal = cmp::min(minimal, solved as u32);

        repeated.insert(c.to_ascii_lowercase(), true);
    }

    minimal
}

fn main() {
    let input = fs::read_to_string("input.txt").expect("Unable to read file");

    println!("solution 1: {}", solve1(&input));
    println!("solution 2: {}", solve2(&input));
}
```

My focus [this time](https://github.com/cesarvr/AOCRust/blob/master/day-5/rewrite/src/main.rs) was to pass just the string (by reference) instead of passing expensive vector copies, then I learn that I can use the ``string::iterator`` to scan the characters and also took the time to simplify some part of the code, when I ran this new version and got this:


```sh
Node   0.17s user 0.03s system 101% cpu 0.209 total
Rust   0.02s user 0.00s system  82% cpu 0.025 total
```
> 8x faster.

Rust welcoming syntax sugar can trick you to believe that the language will handle those ugly details for you, but as we have seen that’s not the case, you require to invest some time profiling and searching until you hit the sweet spot.

Now that Javascript is out of the performance question I wrote a [C/C++ version](https://github.com/cesarvr/AOCRust/blob/master/cpp/2018/day-5/main.cpp) of this puzzle (a very naive and ugly) and this is what I got:

```sh
C++ 0.10s user 0.00s system 87% cpu 0.122 total
```

Not bad, I wonder how elegant and fast can I keep both code bases and of course who could be made faster.
