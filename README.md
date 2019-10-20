# Flask SMS system

NOTE: This is for educational purposes only!

## What is this

This is a project I made for fun to send text messages through the [plivo](https://www.plivo.com).
It's a webserver made in [flask](https://palletsprojects.com/p/flask/) which is a python library.

It is currently set up to automatically convert the inserted phone number to a danish one.

## Setup

To set this script up you need [python3](https://www.python.org) and pip.
To install the requirements via pip, run `pip install -r requirements.txt`

You also need install redis server.

Then you need to create `src/.env` which contains the `auth_id` and `auth_token` for plivo. You can find these on your plivo dashboard. Example:

```env
AUTH_ID="id123"
AUTH_TOKEN="token123"
ADMIN_PASS="pass123"
REDIS_URL="redis://redis123"
```
