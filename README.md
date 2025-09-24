![Python](https://img.shields.io/badge/python-3.13-blue)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![Status](https://img.shields.io/badge/status-alpha-red)

# MangaNotify

MangaNotify is a tool for tracking manga chapter releases via the MangaBaka API and sending notifications to your phone with [Pushover](https://pushover.net). (Discord support planned!)

## Motivation
I wanted a way to get notified when new chapters drop without relying on specific readers or having to check a site manually.

## Features
- Search for manga using MangaBaka API
- Add series to a personal watchlist
- Send notifications via Pushover
- Lightweight UI for search and watchlist
- Run as a Python script or Docker container

## Installation

### Container Startup
**Requirements:** Docker
```bash
git clone https://github.com/gregoryn22/MangaNotify
cd MangaNotify
mv docker-compose.example.yml docker-compose.yml
````
If you would like Pushover notifications, update your credentials and uncomment those lines in the docker-compose.yml file.

`docker-compose up`

Then visit [https://localhost:8999](https://localhost:8999)

### Local Startup
**Requirements:** Python 3.13+
```bash
git clone https://github.com/gregoryn22/MangaNotify
cd MangaNotify
python -m venv .venv
.venv\Scripts\activate    # Windows
source .venv/bin/activate # Linux/Mac
pip install -r requirements.txt
python manganotify.py
```
## Roadmap
- [ ] Add logging
- [ ] Improve UI design
- [ ] Add Discord notifications
- [ ] Improve container usability


# Contributing

This is still early and experimental — feedback welcome!
If I don’t know what I’m doing and can make something at least 20% functional, imagine what you can accomplish 😉
