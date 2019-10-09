
![Werner Vogels About Micro-services At Scale](https://queue.acm.org/detail.cfm?id=1142065)

### Encapsulation

> For us service orientation means encapsulating the data with the business logic that operates on the data, with the only access through a published service interface. No direct database access is allowed from outside the service, and there’s **no data sharing among the services.**

Nothing new here, like with OOP we should isolate the complexity of particular domains inside **objects** and hide the implementation details while providing an access point (methods).


### Divide & Conquer

> The big architectural change that Amazon went through in the past five years was to move from a two-tier monolith to a fully-distributed, decentralized, services platform serving many different applications...


### Improving Reusability


>...We can now build very complex applications out of primitive services that are by themselves relatively simple. We can scale our operation independently, maintain unparalleled system availability, and introduce new services quickly without the need for massive reconfiguration.

Here is an example

> for example this [User]() service.  


### You build it, you run it

This part is key if we really want to implement a DevOps culture, we should work toward facilitating user interaction with their service.

> There is another lesson here: Giving developers operational responsibilities has greatly enhanced the quality of the services, both from a customer and a technology point of view. The traditional model is that you take your software to the wall that separates development and operations, and throw it over and then forget about it. Not at Amazon. **You build it, you run it.** This brings developers into contact with the day-to-day operation of their software. It also brings them into day-to-day contact with the customer. This customer feedback loop is essential for improving the quality of the service.

> Interviewer:  It’s usually internal customers, though, right?

> No, many services are directly customer-facing in our retail applications.



### Should we enforce tools for developers ?

> Developers themselves know best which tools make them most productive and which tools are right for the job. If that means using C++, then so be it. Whatever tools are necessary, we provide them, and then get the hell out of the way of the developers so that they can do their jobs.


> ...Developers are like **artists**; they produce their best work if they have the freedom to do so, but they need good tools. As a result of this principle, we have many support tools that are of a self-help nature. The support environment around the service development should never get in the way of the development itself.



This interview may seem old but it the proof that good engineering practices never. 
