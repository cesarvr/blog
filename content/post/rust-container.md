---
date: "2019-01-17T00:00:00Z"
title: Build A Container Rust Edition 
tags: [Containers, Docker]
draft: true
categories: ["Linux", "Containers", "Rust"]
image: https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/twitter-logos/container_are_linux.png
---

I did a small tutorial some month ago about how to build your own container just using C/C++, but looking at the code I have the impression that some part are very ugly, so I decide to rewrite that in Rust and see how it goes, so lets start by writing our simple hello world. 

## Getting Started

First we need to install rust, you can do that by just writing this in your console: 

```sh 
  curl https://sh.rustup.rs -sSf | sh
```

If you need more details you can go to the [installation page](https://www.rust-lang.org/tools/install).


### Hello World

To start a new project we can use [cargo]() which is a package manager that come with Rust and prepare all the details for us, just go to a folder and write: 

```sh
cargo new container
cd container 

cargo run 

#   Compiling container v0.1.0 (/home/cesar/rust/container)
#    Finished dev [unoptimized + debuginfo] target(s) in 0.31s
#     Running `target/debug/container`

Hello, world!
```

Next step is to get access to the system call in Linux which are exposed by ``libc`` so to do that 



