from flask import Flask, request, render_template, jsonify, redirect, url_for
from flask_httpauth import HTTPBasicAuth
import nexmo
import random, string
from string import digits
from os import getenv
from redis import Redis
from datetime import datetime
from dotenv import load_dotenv
import time, logging
from logdna import LogDNAHandler

load_dotenv()
logkey = getenv("logkey")
app = Flask(__name__)
auth = HTTPBasicAuth()
secret = getenv("secret")
key = getenv("key")
client = nexmo.Client(key=key, secret=secret)
redis = Redis().from_url(getenv('REDIS_URL'))


def genkey(length:int):
	x = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(length))
	return x
def fix_number(number:str):
	if(number == None):
		return None
	number = number.replace(" ", "").replace("+45", "")
	return "45" + number
waiting_receipt = ""
def listen_receipts(posting:bool, data):
	if(posting==True):
		global waiting_receipt
		waiting_receipt=data.args
		print("Delivered " + str(waiting_receipt))
	else:
		print("Getting " + waiting_receipt)
		while waiting_receipt=="":
			time.sleep(1)
			print("Waiting for receipt " + waiting_receipt)
			if(waiting_receipt != ""): break
		print("Sending receipt")
		sent=waiting_receipt
		waiting_receipt=None
		return sent


def sendLog(logdata:str): #Fix pls
	dt = datetime.now()
	redis.lpush("log", "Browser: " + request.headers.get('User-Agent') + " | " + "IP: " + request.remote_addr + " | " + "Timestamp: " + str(dt) + " | " + logdata)

@auth.verify_password
def verify_password(username, password):
	if (username, password) == ("admin", getenv("admin_pass")):
		return True
	else:
		return False

@app.route('/')
def home(): 
	return render_template("index.html")	

@app.route('/admin', methods=['GET', 'POST'])
@auth.login_required
def admin_panel():
	if(request.method == "POST"):
		reciever = fix_number(request.form.get('reciever')) # Make sure it's up to date
		keys = redis.lrange("sms_keys", 0, -1)
		key = genkey(4)
		while key.encode() in keys:
			key = genkey(4)
		if(len(reciever) != 10):
			return jsonify({"Error": "Phone number is not 8 numbers long."}), 400
		message = "Your one time key is: {} \nuse it here: {}".format(key, url_for('admin_panel')) #Make sure this actually works
		try:
			message = client.send_message({'from': "SMSService",'to': reciever,'text': message,})
			sendLog(f"Generated 1 key for {reciever} ({key})") # Might wanna check how it works with sendlog
			return render_template("receipt", data=listen_receipts(False, None), admin=True, key=key) # **Make sure this waits for receipt**
		except Exception as e:
			print(e)
			return jsonify({"Error": "An unknown error occured. Please contact us for more info!"})
	return render_template("admin_panel.html")

@app.route("/DLR-receipts", methods=['GET', 'POST'])
def DLRReceipts():
	if(request.method == "GET"):
		print("DLR receipt: " + str(request.args))
		listen_receipts(True, request)
	return "You've been boofed!"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
