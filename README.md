# Self-hosted alarm system

A multi-platform, self-hosted solution for an alarm system that is customizable and expandable with a multitude of sensors.
The project is designed to run alongside a Raspberry Pi, used for GPIO sensors monitoring, but can be extended (more on that below).

## What it does

A non-complete list of features:
- Create separate users, with different permissions and PINs, and manage them
- Create custom device groups consisting of sensors and RTSP cameras
- When a device group goes in alarm state, relative cameras starts recording
- Cameras can also be set in "always record" mode
- Motion detection with optional person detection (YOLO) on always-recording cameras
- Configurable detection area (ROI) per camera
- Motion warning audio alerts when the alarm is in listening state
- Set your own alarm, waiting, and warning audio per MP3 server
- Receive real time notifications on your phone when alarm is triggered
- Snapshot with detection overlay saved in notification history

## Prerequisites

This project uses [mp3-player-server](https://github.com/WIPtitle/mp3-player-server) for remote audio playback, and [gpio-monitor](https://github.com/WIPtitle/gpio-monitor) for Raspberry's GPIO pins monitoring.
You can install all of this on a Raspberry, thought it is not recommended.

Both gpio-monitor and mp3-player-server should be running and reachable when starting the alarm system.
They should also already be configured: gpio-monitor should already be listening to your desired pins (outputting HIGH when you want a triggered alarm and LOW for idle);
mp3-player-server should be set to use your desired audio output device.

GPIO monitor and MP3 player server URLs are configured from the web interface (Configuration section) after first startup.

Please refer to their specific documentation for installation&configuration, but be aware that they can both be tested before proceeding using
their respective web interface, so if something isn't working stop here and debug that.

As a small note: since gpio-monitor is an external service, you can also write your own monitoring service, as long as it implements the same endpoints.

## Installation

Clone the project on your desired server and run it using Docker. No `.env` file is needed — all configuration is done from the web interface.

```bash
git clone --recurse-submodules https://github.com/WIPtitle/project-core.git
cd project-core
docker compose up -d
```
It will probably take some time to build and run every container.

All timestamps are stored in UTC. The web interface automatically converts them to your browser's local timezone for display.

The system generates a self-signed SSL certificate on first startup. Access the web interface via HTTPS on port 443. For external access, configure port forwarding on your router (port 443 to the server's local IP).

Note: The repository also includes `mp3-player-server` and `gpio-monitor` as submodules for development convenience.
These are **not used** by the main project and must be installed separately on their target servers (typically a Raspberry Pi).

## Usage

When every container is up and running, you can access the web interface on
your server's URL on port 80.

The first user will have admin rights and should be registered now: every other user cannot register himself but should instead be created by the admin user using the User Management section.

Upload your desired alarm MP3 on the Configuration section.

On the Configuration section you can also see the credentials necessary to subscribe to the live alarm notifications using Ntfy.

Create your desired devices on the Devices section: both Sensors and RTSP Cameras have a health check so if creation fails verify that they are reachable.

For cameras with always-recording enabled, you can configure motion detection (motion only or motion + person detection) and optionally set a detection area (ROI) to limit the monitored region.

Create your desired device groups with your specified sensors and/or motion detection cameras. Groups with only cameras will act as warning-only groups (no sensor-triggered alarm). When the alarm is in listening state, motion detection cameras in the group will trigger warning audio and save snapshots with detection overlays.

Activate and deactivate the alarm for your device groups using your PIN, and try to trigger the sensors when alarm is active to verify both audio and notifications.

You can then download recordings on the Recording section. The service will automatically delete the oldest file if memory becomes scarce.
