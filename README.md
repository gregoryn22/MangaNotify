
# MangaNotify

This is a project with the goal of using the MangaBaka API to create a watchlist for manga chapter releases.

The impetus from this project came from finding myself dissatisfied with finding an application that could send notifications upon chapter updates for manga that would be:
1. Agnostic to where you ultimately end up reading it
2. Send some sort of push notifications, rather than necessitating remembering to check a web page.

This project is still under construction.

## About

At this time, the project notifies via Pushover, as that is a service I am familiar with, using it for notification consolidation across several programs. I understand that nowadays this is something most people do through Discord, so at some point I'd like to add that.

The project currently runs both as a local python script that needs to stay open, or in a container. The local version is mostly just for testing/novelty.

### Container Startup

1. run `git clone https://github.com/gregoryn22/MangaNotify`
2. run `cd MangaNotify`
3. change the name of `docker-compose.example.yml` to `docker-compose.yml`
4. run `docker-compose up`
5. using a web browser, navigate to `https://localhost:8999`

## Current Functionality

At this time, the project primarily operates through a window that appears upon running manganotify.py. From this window, you can search using the MangaBaka API, and add search results to your watchlist. There are separate tabs for viewing the watchlist and for viewing the search results.

Right now, you can add your Pushover credentials via settings. 

## Areas currently flawed
1. No logging
2. UI is pretty ugly


# What's next?

Thank you for reading. I hope that this project has inspired you to attempt something similar. If I don't know what I'm doing and can make something at least 20% functional, just imagine what you can accomplish!

# I just want to have my phone buzz when a chapter releases!