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


To take full advantage of Openshift we should change the way we build, deploy and run software. To spark that change here some good engineering principles (that later will become buzzwords on their own) extracted from an interview with [Werner Vogel Amazon's CTO](https://www.allthingsdistributed.com/) on [2006](https://queue.acm.org/detail.cfm?id=1142065).

#### Encapsulation

> We went through a period of serious introspection and concluded that a service-oriented architecture would give us the level of isolation that would allow us to build many software components rapidly and independently... 

> ...for us service orientation means encapsulating the data with the business logic that operates on the data, with the only access through a published service interface. No direct database access is allowed from outside the service, and there’s **no data sharing among the services.**

The advantage here is that a service that owns his data layer then its shielded against external forces changing its state, which is also the same reason why object oriented and functional programming paradigms are very popular. 


### Divide And Conquer

> The big architectural change that Amazon went through in the past five years was to move from a two-tier monolith to a fully-distributed, decentralized, services platform serving many different applications...

>...We can now build very complex applications out of primitive services that are by themselves relatively simple. We can scale our operation independently, maintain unparalleled system availability, and introduce new services quickly without the need for massive reconfiguration.

One of my favorite example of service re-usability is the [Google Subscription](https://myaccount.google.com/payments-and-subscriptions) service: 

![Subscription service](https://github.com/cesarvr/hugo-blog/blob/master/static/static/subscription.png?raw=true)

The Google Subscription service is reusable accross other Google services and creates interesting *synergies*, like for example, the Youtube service can call this service to see if a particular Youtube user is already subscribed to Google Music, and in the affirmative case it will show musics videos with no ads. This not only add value to Google Music subscribers and Youtube, but makes them stronger against competition such as Spotify. 


## You build it, you run it

The he talk of what I think **DevOps** really means: 

> There is another lesson here: **Giving developers operational responsibilities** has greatly enhanced the quality of the services, both from a customer and a technology point of view. The traditional model is that you take your software to the wall that separates development and operations, and throw it over and then forget about it. Not at Amazon. **You build it, you run it.** This brings developers into contact with the day-to-day operation of their software. It also brings them into day-to-day contact with the customer. **This customer feedback loop is essential for improving the quality of the service.**

This philosophy of **You build it, you run it.** not only give more responsabilities to developers, but it also allow developers to target one of the main problems of software development whichs as Sandy Metz saids:

> *"...consumers can't define the software they want before seeing it, so it's best to show them sooner rather than later."*

In other words the people writing the code need a shorter feedback loop between deployments into production, otherwise the **user** won't be able to define the software they want. 


## What tools to use

Another thing I saw on OpenShift customer is the love for controlling the tools their developers use:

> Developers themselves know best which tools make them most productive and which tools are right for the job. If that means using C++, then so be it. Whatever tools are necessary, we provide them, and then get the hell out of the way of the developers so that they can do their jobs...

> ...Developers are like **artists**; they produce their best work if they have the freedom to do so, but they need good tools. As a result of this principle, we have many support tools that are of a self-help nature. The support environment around the service development should never get in the way of the development itself.

This doesn't need to much explanation I guess.


## A Message Of Hope

This interview is from June 30, 2006, it might seem old but let's take a look at the impact of this user centric philosophy on Amazon's market value, on the date that interview was done their market cap was [14 Billions](https://www.wolframalpha.com/input/?i=Amazon+market+cap+June+2006), one financial crisis later their market cap is about [817 Billion](https://www.wolframalpha.com/input/?i=amazon+market+cap), and I have the feeling that they can disrupt any [business they want](https://www.forbes.com/sites/jonmarkman/2018/12/30/amazon-is-feeling-better-about-your-illness/#44ac1b0a4f47). 

The moral of the story might be that either you embrace a culture of DevOps or the Amazon/Facebook/Google/[M$](https://finance.yahoo.com/quote/MSFT/) will embrace it for you. 


