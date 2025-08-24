# Self-hosted alarm system

A multi-platform, self-hosted solution for an alarm system that is customizable and expandable with a multitude of sensors.
The project is designed to run alongside a Raspberry Pi, used for GPIO sensors monitoring, but can be extended (more on that below).

## What it does

A non-complete list of features:
- Create separate users, with different permissions and PINs, and manage them
- Create custom device groups consisting of sensors and RTSP cameras
- When a device group goes in alarm state, relative cameras starts recording
- Cameras can also be set in "always record" mode
- Set your own alarm audio
- Receive real time notifications on your phone when alarm is triggered

## Prerequisites

This project uses [mp3-player-server](https://github.com/WIPtitle/mp3-player-server) for remote audio playback, and [gpio-monitor](https://github.com/WIPtitle/gpio-monitor) for Raspberry's GPIO pins monitoring.
You can install all of this on a Raspberry, thought it is not recommended.

If you install them on separate servers you must update the .env file before running the alarm system,
specifically you have to set GPIO_MONITOR_URL and MP3_PLAYER_SERVER_URL (for example, MP3_PLAYER_SERVER_URL=http://192.168.1.150:8888).

Both gpio-monitor and mp3-player-server should be running and reachable when starting the alarm service.
They should also already be configured: gpio-monitor should already be listening to your desired pins (outputting HIGH when you want a triggered alarm and LOW for idle);
mp3-player-server should be set to use your desired audio output device.

Please refer to their specific documentation for installation&configuration, but be aware that they can both be tested before proceeding using
their respective web interface, so if something isn't working stop here and debug that.

As a small note: since gpio-monitor is an external service, you can also write your own monitoring service, as long as it implements the same endpoints.

## Installation

Make sure to create an .env file (use the .env.example file as base):
Update GPIO_MONITOR_URL and MP3_PLAYER_SERVER_URL if needed, and update PUBLIC_HOST_URL with your public
IP or hostname if you want to access the notifications over the internet.

Clone the project on your desired server and run it using Docker.
```bash
git clone --recurse-submodules https://github.com/WIPtitle/project-core.git
cd project-core
docker compose up -d
```
It will probably take some time to build and run every container.

## Usage

When every container is up and running, you can access the web interface on 
your server's URL on port 80.

The first user will have admin rights and should be registered now: every other user cannot register himself but should instead be created by the admin user using the User Management section.

Upload your desired alarm MP3 on the Configuration section.

On the Configuration section you can also see the credentials necessary to subscribe to the live alarm notifications using Ntfy.

Create your desired devices on the Devices section: both Sensors and RTSP Cameras have a health check so if creation fails verify that they are reachable.

Create your desired device groups with your specified sensors: Cameras that are not always recording will start recording when alarm is triggered.

Activate and deactivate the alarm for your device groups using your PIN, and try to trigger the sensors when alarm is active to verify both audio and notifications.

You can then download recordings on the Recording section. The service will automatically delete the oldest file if memory becomes scarce.