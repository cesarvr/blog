---
title: "DevOps"
date: 2019-10-23
showDate: false
toc: true
description: DevOps.
images:
  - https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
tags: [openshift, build]
draft: true
---


But to take full advantage of this innovation we should consider some changes in the way we build software and to spark a bit of curiosity I've extracted some web service design principles, from an interview with [Werner Vogel Amazon's CTO](https://www.allthingsdistributed.com/) from 2006.

## Writing to an interface

The first interesting point in this interview is the need to write services that hides the implementation details from its consumers, similar to the philosophy of object orientation or good engineering practice in general.

> For us service orientation means encapsulating the data with the business logic that operates on the data, with the only access through a published service interface. No direct database access is allowed from outside the service, and there’s **no data sharing among the services.**

One common anti-pattern on some organizations is to write services passing **foreign keys** as parameters. This is wrong because it brakes the abstraction and tightly couple service and consumers to a particular data base paradigm. 

## Divide And Conquer

> The big architectural change that Amazon went through in the past five years was to move from a two-tier monolith to a fully-distributed, decentralized, services platform serving many different applications...

For me this is one of the best things about OpenShift/Kubernetes, because it make easy to break up big monolith services to create highly distributed services. 


>...We can now build very complex applications out of primitive services that are by themselves relatively simple. We can scale our operation independently, maintain unparalleled system availability, and introduce new services quickly without the need for massive reconfiguration.

One of my favorite example of service re-usability is [Google subscription micro-service](https://myaccount.google.com/payments-and-subscriptions) where in one hand the user can control all its subscription in one place and on the other hand developers can create synergies like, for example, Youtube can check if you are already subscribed to Google Music and provide you with music videos with no-ads.


## You build it, you run it

For me this a key part to really measure your DevOps culture:

> There is another lesson here: Giving developers operational responsibilities has greatly enhanced the quality of the services, both from a customer and a technology point of view. The traditional model is that you take your software to the wall that separates development and operations, and throw it over and then forget about it. Not at Amazon. **You build it, you run it.** This brings developers into contact with the day-to-day operation of their software. It also brings them into day-to-day contact with the customer. **This customer feedback loop is essential for improving the quality of the service.**

In her book [Practical Object Oriented Programming](https://www.amazon.com/s?k=practical+object+oriented+design+in+ruby+2nd&crid=GQX0PRW2RUC0&sprefix=practical+object+%2Caps%2C213&ref=nb_sb_ss_i_1_17) Sandi Metz says that "...consumers can't define the software they want before seeing it", to me this is at the core software that has the customer in mind, we show quick and get feedback earlier, the longer is your deployment/feedback cycle then higher the gap between what the user need and what the software does.

> Interviewer:  It’s usually internal customers, though, right?

> No, many services are directly customer-facing in our retail applications.



### User your own tools

> Developers themselves know best which tools make them most productive and which tools are right for the job. If that means using C++, then so be it. Whatever tools are necessary, we provide them, and then get the hell out of the way of the developers so that they can do their jobs.


> ...Developers are like **artists**; they produce their best work if they have the freedom to do so, but they need good tools. As a result of this principle, we have many support tools that are of a self-help nature. The support environment around the service development should never get in the way of the development itself.



This interview may seem old but it the proof that good engineering practices never.
