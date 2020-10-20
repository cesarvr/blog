---
title: "Performance Showdown: Rust vs Javascript Round 2"
date: 2020-10-20T10:55:00+02:00
draft: false
---


A while ago I wrote a blog post about my learning adventure with Rust by solving some programming puzzle, to my disappointment I found that this naive implementation I wrote wasn’t performant enough to beat a similar one I’ve done in Javascript.

To fix that I profiled the code and found that I was using the slowest function to turn characters lowercase and I ended up replacing that to obtain a symbolic victory, but then discovered that this victory was only in Linux, when I move the code to my MacOS machine I got this:

```sh
Node   0.17s user 0.03s system 101% cpu 0.209 total
Rust   0.23s user 0.01s system 98% cpu 0.238 total
```

This was surprising, but to be honest it was clear that I was just scratching the surface of the problem, so I profiled the code again this time with Instruments on MacOS.  

![](https://github.com/cesarvr/hugo-blog/blob/master/static/rust/malloc-xcode-2.png?raw=true)

It seems that the Rust version is spending the majority of its time doing memory allocation triggered by a ``string:Clone`` method, this is what the Rust docs has to say about it:

> [[Clone]](https://doc.rust-lang.org/std/clone/trait.Clone.html) differs from Copy in that Copy is implicit and extremely inexpensive, while Clone is always explicit and may or may not be expensive...

Well it seems that I got the expensive part here, so I decided to look for the part of my code that might trigger a string clone method, and one of those candidates was ``to_vec`` which the documentation defines as:

> Copies self into a new Vec.

A very economic definition, but I got the idea,  the only problem is that the code was very dependent on ``to_vec`` and I didn’t feel in the mood of starting a discussion with the [borrow checker](https://doc.rust-lang.org/1.8.0/book/references-and-borrowing.html) over how to move things around, so I decided to rewrite the code from scratch.  


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


The key part of the [rewrite](https://github.com/cesarvr/AOCRust/blob/master/day-5/rewrite/src/main.rs) is that instead of passing around vector copies I pass instead a reference to the string I want to reduce, and as a small bonus I stopped removing stuff from collections, in other words I just keep it simple this time and look at the benefits:


```sh
Node   0.17s user 0.03s system 101% cpu 0.209 total
Rust   0.02s user 0.00s system  82% cpu 0.025 total
```
> 8x faster...

So if you need to work on something where low latency is a must then Rust is a good choice, but for Agile microservices JS/NodeJS is my choice after all if you really need performance you can still create a native module to get the best of both worlds. As you see, performance doesn’t come at a free cost. 
