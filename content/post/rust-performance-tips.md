---
title: "Rust Performance Tips"
date: 2020-06-13T07:54:49+01:00
draft: true
tags: [Programming, Performance, Rust]
---


You see when programming on C++ you usually get a welcome message in the form of SEG_FAULT which translates into something similar to a “welcome to hell“ and now you know you are in a kind of dystopian world where you are aware of the presence of some capricious gods. 

With Rust on the other hand, you have the impression that your Javascript tricks will work and there is an interpreter that is going to save your code from being slow. Well that’s wrong as you can see in this snippet for example.


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