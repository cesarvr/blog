Get your Java source code, tested, packaged, containerized and deployed in four steps. We are going to defined 4 decoupled steps that
you can improve with more complex use cases in the future. 


## Step One 

I'm going to start by defining how the container will be created in Openshift, for this we are going to define a build configuration (AKA [BuildConfig](https://cesarvr.io/post/buildconfig/)). 

### What is a BuildConfig?

![](https://github.com/cesarvr/hugo-blog/blob/master/static/static/BuildConfig.png?raw=true)

A BuildConfig is basically an Openshift object that defines how images are constructed in Openshift, they are [four ways to build an image](https://cesarvr.io/post/buildconfig/), we are going to use the **binary** because it give us freedom to choose how to build our software.


### Defining Our BuildConfig 

To define one we are going to use the command line tool ``oc-client`` and it will look like this: 
```sh
oc new-project my-java-services # Creates project 
oc new-build redhat-openjdk18-openshift --binary=true --name=java-microservice 
```
> We create a project with a BuildConfig called ``java-microservice`` using ``redhat-openjdk18-openshift`` as our base and we specify the **binary** flag saying that we want to provide the artifact ourselves.


### Deploying Mechanism

Next we are going to specify how we deploy images created by ``java-microservice``, for this we are going to use a DeploymentConfig, which basically defines how many replicas and keep sure that our containers are always running. 

We need the URL where our image is stored: 

```sh
oc get is 
 #   NAME         DOCKER REPO                                                TAGS      UPDATED
 #   java-microservice docker-registry.default.svc:5000/my-java-services/java-microservice  ... ...
``` 

We define a deployment: 

```sh
oc create deploymentconfig microservice --image=docker-registry.default.svc:5000/my-java-services/java-microservice
```

We automate the deployment when a new image is created (Optional): 

```sh
oc set triggers dc/microservice --from-image=docker-registry.default.svc:5000/my-java-services/java-microservice:latest -c default-container
```
> We define that we want to re-deploy our services each time a new image with tag ``:latest`` is created. 

### Traffic

Last step is to configure the traffic allowing our containers to receive traffic: 

```
# To expose this container to the cluster.
oc expose dc/microservice --port 8080  

# To expose this service to the internet.
oc expose svc/microservice --port 8080  
```














