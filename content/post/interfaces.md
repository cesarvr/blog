---
title: "Power of interfaces."
date: 2018-09-17
showDate: false
toc: true
draft: true
description: ""
images:
  - https://github.com/cesarvr/hugo-blog/blob/master/static/static/logo/ocp.png?raw=true
tags: [OOP, design]
---

Whats the different of good code versus bad code, for me; is the code that fails to tell you what it does. If you or your teammates struggle to understand what the code is doing then the code becomes to difficult to maintain.

We are going to use one of the most "loved & hated" language C++ just to demonstrate how beautiful code has more to do with how do we write code and less about the tools we use.

<!--more-->


## Start

We are going start our with this initialization code a copy from the Linux man pages:

```c++
int main() {

  int socket_desc , client_sock , c;
  struct sockaddr_in server , client;

  socket_desc = socket(AF_INET , SOCK_STREAM , 0);
  if (socket_desc == -1)
  {
      printf("Could not create socket");
  }
  puts("Socket created");

  server.sin_family = AF_INET;
  server.sin_addr.s_addr = INADDR_ANY;
  server.sin_port = htons( 8888 );

  //Bind
  if( bind(socket_desc,(struct sockaddr *)&server , sizeof(server)) < 0)
  {
      //print the error message
      perror("bind failed. Error");
      return 1;
  }
  puts("Listening in http://localhost:8888");

  //Listen
  listen(socket_desc , 3);

  int len = sizeof(struct sockaddr_in);  

  while( (client_sock = accept(socket_desc, (struct sockaddr *)&client, (socklen_t *) &len )) )
  {
     puts("Connection accepted");

     handle_client(client_sock);
  }
}
```

First we notice is that this code is failing to tell the story of whats trying to do. This failure is not only making this code more difficult to read but also it make it more difficult to change or test.

Let's start by isolating things we want to change that things that we don't want to change to much. First let isolate the code that do the setup in its own function.

```c++
class Server {
  private:
    int socket_descriptor, port;
    struct sockaddr_in configuration;

  public:
    Server(){

      socket_descriptor = socket(AF_INET , SOCK_STREAM , 0);

      if (socket_desc == -1)
      {
          printf("Could not create socket");
      }

      //Prepare the sockaddr_in structure
      configuration.sin_family = AF_INET;
      configuration.sin_addr.s_addr = INADDR_ANY;
      configuration.sin_port = htons( port );
    }
};
```

I'll create a class here and we are going to use the constructor of the class to handle the initialization of our server. we are going to change the ```server``` variable and we are going to called ```configuration``` which resembles the real purpose of that variable in the context of this class.

One the stuff that doesn't change is that Linux system calls follows a convention of returning -1 in case of error and the publish the error message through ```perror```, function as convention are like rules so we are going to take advantage a make a generalization out of this.  

```c++
void checkForErrors( int code, string mess){
  if(code == -1)
  {
    perror(mess.c_str());
    exit (EXIT_FAILURE);
  }
}
```

Now we can replace this:

```c++
  if (socket_desc == -1)
  {
      printf("Could not create socket");
  }
```

With this:

```c++
  checkForErrors(socket_descriptor, "Can't create a socket");
```


Now our newly organized version looks something like this:


```c++
class Server {
  private:
    int socket_descriptor, port;
    struct sockaddr_in configuration;

  public:
    Server(int port): port{port}{
      socket_descriptor = socket(AF_INET , SOCK_STREAM , 0);

      checkForErrors(socket_descriptor, "Can't create a socket");

      configuration.sin_family = AF_INET;
      configuration.sin_addr.s_addr = INADDR_ANY;
      configuration.sin_port = htons( port );
    }
};
```

Now we need to take care of the actions of our server, let's refactor the rest of the code inside a descriptive function name.

```c++
template <typename Callback>
void waitForConnections() {
  auto status = bind(socket_descriptor,
                     (struct sockaddr *)&configuration ,
                     sizeof(configuration));

  checkForErrors(status, "bind failed.");

  //Listen
  listen(socket_descriptor , 3);
  cout << "listening in port: " << port << endl;


  auto len = sizeof(struct sockaddr_in);
  while(true)
  {
    struct sockaddr address;

    // blocking here.
    auto socket  = accept(socket_descriptor,
        (struct sockaddr *)&address, (socklen_t *) &len );

    cout << "connection accepted" << endl;
    handle_client(socket);
  }
}
```

First thing I did here is to change the name of the variables and implemented our error handling function.
Also we, make our server to wait forever, the other version just worked for the one client. We put this code in a C++ header file called ```network.h```.


## Improve

When we implement the new version of our code it will look to something like this.

```c++
int main(){
  cout << "thread pool example" << endl;
  Server server{8080};

  server.waitForConnections();
  return 0;
}
```

Now this code looks more better, just by a quick look of this code we are able to see what this code does. 



But how is this happening ? Some people quick reaction is to blame the language and they are maybe right, those data structure names, don't make the job easier, if you don't come from the Unix/Linux system programming background. But this code is also failing to encapsulate this complexity and thats I believe is the major flaw here, the person that wrote this code fail identify and separate the behavior in this code.


## First identify the behavior

What we want to write is a simple but scalable TCP server. Easy to modify that takes some request and simply respond to the callee with some arbitrary response.






## Power of Interfaces.

Take a look now at this code.


```c++

int main(){
  cout << "thread pool example" << endl;

  Server server;

  server.setPort(8080);

  server.waitForConnections(handleConnection(auto fd_server) {
    //handle this thing...
  });

  return 0;
}
```

Not only the code is more shorter but now the code is explaining what it does, removing the need to use comments. You might say that the only thing I did was hide the complexity behind those methods and is true, because that's one of the power of writing to an interface and also that's the power of object oriented programming, is to isolate and organize behavior.

This was a bit like an hyperbolic example on how to abstract behavior but visiting clients I have saw the following code, in a higher level language like Javascript.

```js
class ProgressBar {
  constructor({percentage}) {
    this._percentage = percentage

    if(_percentage < 0 )
      this._percentage = 0

    if(_percentage > 100)
      this._percentage = 100

    //...
  }


  get percentage() {
    return this._percentage
  }

}

```

This code is another example, the problem here, is that the constructor is doing to much and by just reading this code we are not sure of what that code is doing, again, the writer of this code is failing to communicate what is trying to do.

```js
class  ProgressBar {
  constructor({percentage}) {
    this._percentage = this.setPercentage(percentage);
  }

  setPercentage(value) {
    let percentage = value

    if(percentage < 0 )
      percentage = 0

    if(percentage > 100)
      percentage = 100

    return percentage;
  }

}
```

With this new version of the code, you can comeback 2 years later and just by scanning ```setPercentage``` you can know what this code is trying to do and the best thing is there is no need to add any comments.
