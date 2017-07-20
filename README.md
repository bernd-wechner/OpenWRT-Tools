# OpenWRT-Tools

Some simple CLI tools for use on my OpenWRT router.

All experimental and just whipped up as needed for quick easy insights into what is going on without relying on the web interface of the router to be up and running. 

I install most of them them in /root/bin, ensure the scripts are executeable and add $HOME/bin to my path in .profile, so when I ssh to the router I can quickly access any of these for some tuned insights into what I want to know.

There is one trick problem that takes a special solution, a remotely hosted web page wich can receive WAN IP logs from my OpenWRT router whenever it changes, and report some diagnostics comparing the logged WAN IP with what it seees on the net as the IP for my domains, and also what NameCheap (my registrar) reports as the configured IP address for exach domain.

Because it's on a remote host with a static and known IP, the site can access the NameCheap API (which only works for whitelisted client IPs, to wit, if my routers IP changes I can't access it from the router) and I can visit it from wherever I am or even check on my phone, what the DDNS configs are doing and if they are playing up.