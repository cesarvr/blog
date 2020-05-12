---
title: "Creating A SSH Tunnel To Connect Via RDP"
date: 2020-04-08T09:27:00+01:00
draft: false
tags: [vpn, cheatsheet]
---

I'm working at the moment for a company that use an OS (and spyware) Windows 10 and because of some [world wide events](https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_the_Republic_of_Ireland) I started like everybody else to work remotely and connect to my desk machine remotely via VPN.

To achieve this the IT department recomended the use of something called Cisco Anyway Connects which is a sort of VPN client.

The problem is that because I use a flavor of BSD at home I've to think on how to use that Cisco thing that only works on ``Winx86`` to make the VPN while keeping myself far from Windows.

My solution was to create a Virtual Machine to put all the required VPN software there and setup a [SSH](https://en.wikipedia.org/wiki/Secure_Shell) tunnel to access my work machine through the VM-VPN and use my OS to work or RDP as needed.


Here some instructions:

  * Install [Windows 10](https://www.microsoft.com/en-gb/software-download/windows10ISO) spyware in a virtual machine it will require 16 GB of disk space but if you run the [Win10 Debloater](https://github.com/Sycnex/Windows10Debloater) you can make it almost usable.

  * Install [OpenSSH Server](https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse) (yes they try to be cool now).

  * Make sure you start the [OpenSSH](https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse) service.

	![](https://github.com/cesarvr/blog/blob/master/static/ssh-tunnel/service.png?raw=true)

  * Open a CMD screen inside the VM and run:

  ```sh
    ssh -fNTC -L *:20000:<machine-to-rdp-to>:3389 <local-ssh-user>@localhost
  ```

 - This ``<local-ssh-user>@localhost`` should point to the local Windows account user.

 - The tunnel definition ``-L *:20000:<machine-to-rdp-to>:3389`` means that the traffic will be tunneled **from** the *remote* RDP port ``3389`` **to** a *local* port that I choose at random ``20000``.

	> The ``*`` means that everybody can connect, if you are running inside a NAT protected virtual machine (like myself) this should be fine. If you want to do this in a machine in the cloud you will restrict that to your own IP address.  


- Last thing is to forward the port ``20000`` to the Host OS:

	![](https://github.com/cesarvr/blog/blob/master/static/ssh-tunnel/port-forward.png?raw=true)


Now I just need to connect via RDP using this URL:

```sh
127.0.0.1:20000
```
