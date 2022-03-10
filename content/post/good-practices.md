---
title: "About The S In Solid and Commenting Code"
date: 2022-03-10
draft: false
keywords: []
description: "About The S In Solid and Commenting Code."
tags: [Programming]
toc: true
image: https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
---

Some times I surprise about having to discuss the same subject over and over, but as consultant thats one of the advantage and disadvantage. The advantage you get out of your own bubble and meet other devs as part of your work and the disadvantage is that sometimes you need to sometimes discuss same subjects that you take for granted. I will publish a couple of post around good coding practices in order to have something to synthesize my ideas around the subject. 

In this post I would like to touch two subjects the "Single Responsability Principle" and "Comments In Code".    

### Single Responsability Principle 

Basically this principle says that you should write classes that just one thing. And the only way two classes can interact is by using public interfaces. 

* Here are some book recommendations that expand around this subject: 
    * [**Practical Object-Oriented Design: An Agile Primer Using Ruby**](https://www.amazon.es/Practical-Object-Oriented-Design-Agile-Primer/dp/0134456475/?_encoding=UTF8&pd_rd_w=ACbCs&pf_rd_p=24b43a27-c0ae-4ea6-b5f2-9efedefa0bf7&pf_rd_r=KGATXB2CN32V0WHPP57B&pd_rd_r=7fc1266b-528a-433e-9e32-2916364bb448&pd_rd_wg=pBSZs&ref_=pd_gw_ci_mcx_mr_hp_d) 
        * “**Chapter 4** Flexible Interfaces” takes a deep dive into this subject.  
    * [The Pragmatic Programmer](https://www.amazon.es/Pragmatic-Programmer-journey-mastery-Anniversary/dp/0135957052/ref=sr_1_1?__mk_es_ES=ÅMÅŽÕÑ&crid=36NFGHHPPKL3G&dchild=1&keywords=pragmatic+programmer&qid=1621258055&sprefix=pragma%2Caps%2C256&sr=8-1) 
        * **"Chapter 10 Orthogonality"** also mentions the benefits of this way of working.   
    * [Head first: Design Patterns](https://www.amazon.es/First-Design-Patterns-Brain-Friendly/dp/0596007124/ref=sr_1_1?__mk_es_ES=%C3%85M%C3%85%C5%BD%C3%95%C3%91&dchild=1&keywords=head+first&qid=1621268160&sr=8-1) 
        * This book was the first one I read around the design patterns subject. 
        * The **Chapter 1** of this books is dedicated to this subject of how we can take advantage of interfaces to add flexibility to our code."   

### About Comments In Code

I’m of the opinion that unless you are trying to describe an obscure assembler interaction or a cool (non-trivial to understand by reading the code) trick that will provide  10x performance, we should keep comments to a minimum for non-customer facing API. 

To arrive to that conclusion, I got the inspiration from the following books:

#### Refactoring: Improving the Design of Existing Code (Martin Fowler) 

The opinion in this book is that if you find a comment in the code explaining what block of code does, we should take this as an opportunity to refactor this block into a set of functions or classes that express its purpose.  

##### Quotes: 

> "Replace comments with good function names (refactor if necessary).  

If everything fails: 

> "A good time to use a comment is when you don’t know what to do. In addition to describing what is going on, comments can indicate areas in which you aren’t sure. A comment can also explain why you did something. This kind of information helps future modifiers, especially forgetful ones."

### The Pragmatic Programmer: 

They suggest that comments are good if you have the right tools to transform comments into documentation: 

> “It’s easy to produce good-looking documentation from the comments in source code, and we recommend adding comments to modules and exported functions to give other developers a leg up when they come to use it."

However:

> "This doesn’t mean we agree with the folks who say that every function, data structure, type declaration, etc., needs its own comment. This kind of mechanical comment writing actually makes it more difficult to maintain code: now there are two things to update when you make a change.”


And for me the most important point, the maintenance cost behind comments: 
            
> This kind of mechanical comment writing actually makes it more difficult to maintain code: now there are two things to update when you make a change.”


#### Practical Object-Oriented Design: An Agile Primer Using Ruby 

Ironically I don't usually work with the Ruby language but this is my favorite book so far on coding practices and design patterns, the author starts by discussing the costs of having comments and propose the same philosophy we saw earlier of "replace comments with better code": 

> “**How many times have you seen a comment that is out of date?**     Because comments are not executable, they are merely a form of decaying documentation. If a bit of code inside a method needs a comment, extract that bit into a separate method. The new method name serves the same purpose as did the old comment.”  

