---
title: "Deploying Applications in Openshift"
date: 2018-07-31T10:05:23+01:00
lastmod: 2018-07-31T10:05:23+01:00
draft: false
keywords: []
description: ""
tags: [openshift, imagestream]
categories: []
author: ""

# You can also close(false) or open(true) something for this content.
# P.S. comment can only be closed
comment: false
toc: false
autoCollapseToc: false
# You can also define another contentCopyright. e.g. contentCopyright: "This is another copyright."
contentCopyright: false
reward: false
mathjax: false
---

<!--more-->


[We got our image created what next ?](http://cesarvr.github.io/post/deploy-ocp/) How do we trigger deployments when a specific image get pushed or when the image tag change ? [Image streams](https://docsropenshift.com/enterprise/3.0/architecture/core_concepts/builds_and_image_streams.html#image-streams) is the Openshift answer to those existential questions, the work by listening to images changes in the registry and then notify their subscribers of this change.        

Images streams objects are created in two ways by importing an image to the cluster:  

```
oc import-image microservice:latest --from=your-docker-registry.io/project-name/cutting-edge:latest --confirm

# ImageStream. 
oc get is

NAME             DOCKER REPO
microservice:latest      docker-registry.default.svc:5000/hello01/cutting-edge:latest
```   

This create a image stream called *microservice*, every time this image change (a new version is pushed), the image stream will notify any resource subscribed to it. This resource can be a Jenkins pipeline that run some security check over this image, DeployConfig that will deploy this image, another BuildConfig (see [chain build](http://cesarvr.github.io/post/ocp-chainbuild/)), etc.   

 
The other way is by creating a [BuildConfig](http://cesarvr.github.io/post/deploy-ocp/) this objects creates an image from source code and push this image to the registry, to monitor this the image an image stream is also created:  

```
# new BuildConfig
oc new-build nodejs~https://github.com/cesarvr/hello-world-nodejs --name node-build

# ImageStream. 
oc get is

NAME             DOCKER REPO
node-build       docker-registry.default.svc:5000/hello01/node-build
```   


# Deploy

To deploy the latest images we just need to create a deployment configuration that subscribe to the image stream. I'll arbitrarily choose the ```node-binary``` build, but this steps can be reused for all the images streams we have created so far.

```sh
oc get is

NAME          DOCKER REPO                                            TAGS      UPDATED
node-binary   docker-registry.default.svc:5000/hello01/node-binary   latest    27 minutes ago
```

Having the address of our image, now we just simply call:

```sh
oc create dc hello-ms --image=172.30.1.1:5000/hello/runtime
```

Now that we create our deployment object called ```hello-ms``` and subscribed to the ```node-binary``` image stream, we now need to send some traffic to our application. Let's find the labels of our new deployment object.

```sh
oc get dc hello-ms -o json | grep labels -A 3
# returns
"labels": {
            "deployment-config.name": "hello-ms"
          }
```

Now let create a service and send some traffic directed to objects with ```deployment-config.name: hello-ms```  label:

```sh
oc create service loadbalancer  hello-ms --tcp=80:8080
# service "hello-ms" created

# edit the service object
  oc edit svc hello-ms -o yaml
```

This will open the service object in yaml format in edit mode, we need to locate the *selector* and replace with the label of our deployment object.

From this:

```yml
selector:
  app: hello-ms
```

To this:

```yml
selector:
 deployment-config.name: hello-ms
```

We can do this the other way around, at the end is just a matter of taste. Next we need to expose our service:

```
oc expose svc hello-ms
# route "hello-ms" exposed

oc get route
NAME       HOST/PORT                                                   PATH      SERVICES     PORT          
hello-ms   hello-ms-hello01.7e14.starter-us-west-2.openshiftapps.com              hello-ms   80-8080                
```

Now know the URL we can confidently make a ```curl``` to that address:  


```
curl hello-ms-hello.127.0.0.1.nip.io
Hello World%
```

If my pod are not in sleeping mode (remember is a demo instance). You can access it using this [URL](http://hello-ms-hello01.7e14.starter-us-west-2.openshiftapps.com/).


