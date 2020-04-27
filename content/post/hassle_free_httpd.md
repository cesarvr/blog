---
title: "How to Quickly Serve Statics Files On Openshift"
date: 2020-04-09T09:52:31+01:00
draft: false
tags: [openshift, HowTo]
---

We can start by creating a folder to store the static files: 

```bash
mkdir mystatic 
```

<!--more-->

Copy the static content you want to serve, in this example we are going to serve a simple ``index.html`` file:

```bash
# Jump into the folder
cd mystatic


# Download index.html *Hello World*
curl https://gist.githubusercontent.com/timbergus/5812402/raw/10ed8484a7b71d0f860f6cc0d81f5fafcf9ef339/index.html -o index.html 

cat index.html

<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hello World! Site Title</title>
  </head>
  <body>
    <h1>Hello World!</h1>
  </body>
</html>%
```


### Choose Your Server

We are going to use [httpd](https://httpd.apache.org/) to handle the serving the files, we can find if we have this container:  

```bash
oc get is -n openshift | grep httpd

#httpd  ...default.svc:5000/openshift/httpd  2.4, latest...
```

Look like we have ``httpd`` available, so let's use this to create a new image with the content of the ``mystatic`` folder we created above: 

```bash
# Make the configuration for our image builder
oc new-build httpd --name=static --binary=true

# ...and build our image using the content of our directory.
oc start-build static --from-file=mystatic --follow
```

Then deploy the image: 

```bash
# Find the created image...

oc get is
# ...docker-registry.default.svc:5000/ctest/static...

# Deploy this image into a container.
oc create dc my-statics --image=docker-registry.default.svc:5000/ctest/static:latest
```


And configure some traffic to our container:

```bash
  oc expose dc/my-statics —port=8080
  oc expose svc/my-statics

  # Now that the traffic is configured, we can access with our browser the following URL.
  
  oc get routes
  # https://your-route-to-container

```


### Reload 

The idea is to do all this configuration once and from now any new update just create and deploy a new image without to much troubles, so let's make a script to automate this: 

```bash
#!/bin/bash

oc start-build static --from-file=. --follow  # Push content from current folder
oc rollout latest dc/my-statics # redeploy the image
```
We save this as ``reload.sh``, make it executable: 

```bash
chmod +x reload.sh 
```

And we can reload the content: 

```bash
./reload.sh
#---> Enabling s2i support in httpd24 image
#...
#...
# Pushing image docker-registry.default.svc:5000/ctest/static:latest

```
We should have our assets deployed. 

### Another way 

Is to configure deployment configuration to watch for changes in the image, we just need to modify the script: 

```bash 
#!/bin/bash
oc start-build static --from-file=. --follow  # Push content from current folder

### oc rollout latest dc/my-statics # remove this line
```

And setup the trigger: 

```bash
#oc set triggers dc/<deployment-config> --from-image=<namespace>/imagestream:tag -c default-container

oc set triggers dc/my-statics --from-image=ctest/statics:latest -c default-container
```


### Securing Traffic

To secure the traffic via TLS (HTTPS) you just need open the router in the console: 

```bash
oc edit route my-statics 
```
Go to this section:

```yaml
spec:
  host: my-statics-ctest.e4ff.pro-eu-west-1.openshiftapps.com
  port:
    targetPort: 8080
```

And add just below ``port``: 

```yaml
spec:
  host: my-statics-ctest.e4ff.pro-eu-west-1.openshiftapps.com
  port:
    targetPort: 8080
  tls:
    termination: edge
```

Now you can access your static content via HTTPS. 


### Reducing Load 

Unless you are expecting millions of request you can optimize this build by reducing the memory this container can consume:

```bash 
spec:
   containers:
      - image: docker-registry.default.svc:5000/ctest/static:latest       …
```
And just below image add this: 

```bash 
spec:
   containers:
      - image: docker-registry.default.svc:5000/ctest/static:latest
      resources:
         limits:
            memory: 80Mi
```

> This will be nice if your cluster admin impose quotas on your cluster.

