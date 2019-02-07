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

```cpp
using Parsers = map <string, function<void(string&&)>>;

void JSONParser(string&& data){
  cout << "parsing json: " << data << endl;
}

void XMLParser(string&& data){
  cout << "parsing xml: " << data << endl;
}

// More parsers...

int main() {
  Server server;
  Parsers parsers = { {"json", &JSONParser }, {"xml",  &XMLParser  } /*...*/ }; 

  auto reader = parsers[ server.protocol() ];

  if(reader == nullptr)
    printf("Don't know this protocol ...\n");
  else 
    reader(server.payload());

  return 0;
}
```

This beautiful code allow us to select a behaviour at runtime, this is type generic programming is what I like in a programming language, that give me the tools to create flexible code. Here I just need to add more parser as needed in the future. 

Let see if we can achieve this in Rust. 


```rust
type P<'a, 'b> = HashMap<&'a str, &'b Fn(String)>;

fn read_json(data: String){
    println!("Reading JSON {}", data);
}

fn read_xml(data: String){
    println!("Reading XML {}", data);
}

// More parsers...

fn main() {
    let server = Server{ name: "localhost".to_string() };
    let mut parsers: P = HashMap::new();

    parsers.insert("xml",  &read_xml);
    parsers.insert("json", &read_json);

    /* Server send compatible format ... */
    let protocol = &server.protocol();
    if let Some(parser)  = parsers.get::<str>(&protocol) {
        parser(server.payload());
    }else {
        println!("Don't know this protocol..."); 
    }
}
```

Aside from the syntactic sugar for ``HashMap`` initialization, it looks great. This code achieve the same polymorphism at runtime.

Now can we do a more sophisticated type like with objects instead of functions ? 












