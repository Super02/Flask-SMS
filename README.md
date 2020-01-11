# Flask-SMS
---
### This is a system to send SMSes and make calls through a website, using flask.
---
### Setup & Installation
* You need to buy a service named Nexmo for this to work you can buy it [here](https://www.nexmo.com/).
* To install and setup this project clone this project down locallay using GitHub clone button. ![Clone](https://raw.githubusercontent.com/Super02/Flask-SMS/master/images/clone.jpg)
* When you've done that you need to create some environment variables. Create the following variables:
```env
admin_pass="Admin Password for Admin Site"
key="Nexmo key"
secret"Nexmo secret
logkey="LogDNA key"
mbird_testkey="MessageBird testkey" #Not required
messagebirdkey="MessageBird key"
```
### Usage
![Index](https://raw.githubusercontent.com/Super02/Flask-SMS/master/images/index.jpg)
Run index.py, and watch your website running at localhost:5000.
You can then fill out the fields and press submit to see the action!
### Customisation
![Customize](https://raw.githubusercontent.com/Super02/Flask-SMS/master/images/Variables.jpg)
Edit these variables as you please.
### Credits to:
* @ViggoGaming - for helping designing this project, and helping a little bit with the code.
* @dnorhoj - for coming up with the idea to make this project.
