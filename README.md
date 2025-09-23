
# MangaNotify

This is a project with the goal of using the MangaBaka API to create a watchlist for manga chapter releases.

The impetus from this project came from finding myself dissatisfied with finding an application that could send notifications upon chapter updates for manga that would be:
1. Agnostic to where you ultimately end up reading it
2. Send some sort of push notifications, rather than necessitating remembering to check a web page.

This project is still under construction.

## About

At this time, the project notifies via Pushover, as that is a service I am familiar with, using it for notification consolidation across several programs. I understand that nowadays this is something most people do through Discord, so at some point I'd like to add that.

The project currently runs as a local python script, needing to stay open. The goal is deployment through a container so that you can run this and forget about its existence until you get your notifications. I'd be surprised, but I could also see someone preferring it to exist as an application living in your system tray.

## Current Functionality

At this time, the project primarily operates through a window that appears upon running manganotify.py. From this window, you can search using the MangaBaka API, and add search results to your watchlist. There are separate tabs for viewing the watchlist and for viewing the search results.

Right now, you can add your Pushover credentials via settings. 

## Areas currently flawed
1. No logging
2. UI is pretty ugly

## What's Next?
The next thing I'll probably tackle will be updating this to exist in a container. From there, it shouldn't take that much work to make it look a little better and add some backend logging.

Thank you for reading. I hope that this project has inspired you to attempt something similar.

I just want to have my phone buzz when a chapter releases!