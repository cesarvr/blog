---
title: "Meta-Programming in Rust"
date: 2019-01-15
draft: true
keywords: []
description: "Rust"
tags: [rust, meta-programming]
categories: [rust, meta-programming]
toc: false
image: https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/dashboard.png?raw=true

---

The first thing was to read the puzzle input, a plain text where the  

```xml 
#1 @ 1,3: 4x4
#2 @ 3,1: 4x4
#3 @ 5,5: 2x2
```  

```rust
fn read_list(file_name: &str) -> Vec<Claim> {

    let list = fs::read_to_string(file_name).expect("file not found");
    let claims = list.lines().map( get_claim ).collect::<Vec<Claim>>();

    for claim in &claims {
        println!("Claim id {}: x:{} y:{} , w:{}, h:{}", claim.id, claim.x, claim.y, claim.width, claim.height );
    }
    claims
}




fn main() {
    let claims = read_list("./test.txt");

}
```



Here is a simple Rust meta-programming example: 

```rust
  macro_rules! four {
      () => {1+3};
  }

  fn main() {
      println!("magic -> {}", four!() );
  }
```

