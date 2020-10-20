---
title: "Performance Showdown: Rust vs Javascript Round 2"
date: 2020-10-20T10:55:00+02:00
draft: false
---

A while ago I wrote a [blog post](https://cesarvr.io/post/rust-performance/) post about my learning adventure with Rust, to make thing interesting I was trying to use Rust to solve some [programming puzzle](https://adventofcode.com/2018/day/5) and by curiosity I decided to use this puzzle as a benchmark to measure what language was faster Rust or Javascript.

On paper the winner should be Rust by a mile, but I found out that that wasn’t the case and JS was faster. Looking for the reason for this I started to profile the Rust code looking for bottlenecks and found that interestingly I was using the [slowest function to turn characters lowercase](https://cesarvr.io/post/rust-performance/), giving my naive Rust code a temporary victory.

That was until I move the code to my MacOS machine, which by curiosity I decide to give it try just by chance:


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

The main focus [this time](https://github.com/cesarvr/AOCRust/blob/master/day-5/rewrite/src/main.rs) was to pass the string by reference instead of passing vector copies (looking back now seems like obvious), use the ``string::iterator`` to scan the characters and as a small bonus I simplify the matching and reducing of letters, when I ran this new version and got this:


```sh
Node   0.17s user 0.03s system 101% cpu 0.209 total
Rust   0.02s user 0.00s system  82% cpu 0.025 total
```
> 8x faster, not bad :)

All this happens because of some preconceived ideas I had about Rust, that high level syntax had tricked me to believe that it was a high level language when in reality behind all that syntax sugar it requires you to be aware of not only the low-level details but also how the language implements certain things in order to write efficient software. It was that or just JS had made me softer.

In other words, getting performance out of Rust is not free and I suspect that this learning curve will be the main challenge to become widely adopted. But definitely good choice if you want to write difficult to exploit code with close to C/C++ performance.

Talking about that I wrote a C/C++ version of this puzzle (a very naive version not an expert in C++) and this is what I got:

```sh
C++ 0.10s user 0.00s system 87% cpu 0.122 total
```

I will do some experimentations now and see if I can get it faster and maybe try to write a blog entry about it.
