Get your Java source code, tested, packaged, containerized and deployed in four steps. We are going to defined 4 decoupled steps that
you can improve with more complex use cases in the future. 


## Step One 

Let's start by defining how the container will be created in Openshift, for this we are going to define a build configuration (AKA [BuildConfig](https://cesarvr.io/post/buildconfig/)). 

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

![](https://raw.githubusercontent.com/cesarvr/hugo-blog/master/static/static/backbone.PNG)

Now we got our backbone ready to deploy any image created by our ``java-microservice`` **BuildConfig**, now the next step is trigger this by sending a binary tested and packaged by **Jenkins**.   

## Step Two

This part assumes that you already have Jenkins deployed and running in your Openshift cluster, if you haven't do this before, I've wrote [this small guide](https://github.com/cesarvr/Spring-Boot#configuring-continuous-integration) to help you get the basics, you can comeback to this point when you finnish the installation. 

One advantage of doing our build configuration using the binary strategy is that it give us a "common interface", meaning that it doesn't matter if we build our binary with Gradle, Maven or Ant; this build just require that we provide a JAR file. 

Spring Boot offers a way to create light weight microservices using an embeded Tomcat, so [let's containerize a Spring Boot ](https://github.com/cesarvr/GradleOpenShift) microservice using Gradle.  

Now let's create a simple Pipeline: 

![](https://github.com/cesarvr/Spring-Boot/blob/master/docs/newPipeline.png?raw=true)

No we open this pipeline project and go to the scripting part and we define the tools and some variables: 

```groovy
def project = "my-java-services"   // we've created this using oc new-project...
def clusterName = "your-openshift-endpoint" // Example: https://openshift.console.org. 
def imageBuildConfig = "java-microservice"  // The one we created above.
def GIT_URL = "https://github.com/cesarvr/Spring-Boot" // Your Spring Boot project. 

pipeline {
  agent any
 
  tools { 
    gradle 'Gradle562' // You can setup this using Jenkins Global Tools. 
  }
}
```

We instruct Jenkins to clone, test and package our Java binary: 

```groovy
   stages {
        
    /*=============================================*/
    /* Clone the project                           */
    /*=============================================*/
        
    stage('Preparation'){
        steps {
             git GIT_URL
        }
    }
    
    /*=============================================*/
    /* We keep Maven related stuff here            */
    /*=============================================*/
        
   stage('Testing And Packaging') {
        steps {
            sh   'gradle build'
        }
    }
    /*=============================================*/
``` 

And finally we need to deploy our JAR binary into our BuildConfig: 


```groovy
   stage('Build') {
          
        steps {
            echo "Pushing The JAR Into OpenShift OpenJDK-Container"
            script {
                openshift.withCluster( clusterName ) {
                    openshift.withProject( project ) {
                        openshift
                        .selector("bc", imageBuildConfig)
                        .startBuild("--from-file=build/libs/gs-spring-boot-0.1.0.jar", "--wait")
                    }
               }
              }
          }
    	  
          post {
            success {
              archiveArtifacts artifacts: 'build/libs/**.jar', fingerprint: true
            }
          }
        }
    }
``` 

> Here we are using [Openshift DSL Plugin](https://github.com/openshift/jenkins-client-plugin) to select the BuildConfig (``java-microservice``) and provide the binary and block the task until the container is created.  









