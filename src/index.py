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
import json
import traceback
import pprint
import smtplib
from uuid import getnode as get_mac
import requests
import math
import phonenumbers

formatter = phonenumbers.AsYouTypeFormatter("DA")
load_dotenv()
logkey = getenv("logkey")
app = Flask(__name__)
auth = HTTPBasicAuth()
secret = getenv("secret")
key = getenv("key")
client = nexmo.Client(key=key, secret=secret)
redis = Redis().from_url(getenv('REDIS_URL'))
waiting_receipt = ""
redis.set("receipt", "")
log = logging.getLogger('logdna')
log.setLevel(logging.INFO)
log = logging.getLogger('logdna')
log.setLevel(logging.INFO)
timestamp=[]
def format_number(number:str):
	z = phonenumbers.parse("+" + number, None)
	return(phonenumbers.format_number(z, phonenumbers.PhoneNumberFormat.INTERNATIONAL))

options = {
  'hostname': 'SMSService',
  'ip': '10.0.1.1',
  'mac': 'C0:FF:EE:C0:FF:EE'
}
options['index_meta'] = True
test = LogDNAHandler(logkey, options)
log.addHandler(test)

print("Starting up...")

def isInt(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False
def genkey(length:int):
	keys = redis.lrange("sms_keys", 0, -1)
	x = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(length))
	while key.encode() in keys:
		x = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(length))
	return x

def fix_number(number:str):
	if(number == None):
		return None
	number = number.replace(" ", "").replace("+45", "")
	return "45" + number
def listen_receipts():
	time.sleep(0.1)
	for x in range(25):
		time.sleep(1)
		print(f"{x}/25 Waiting for receipt " + str(redis.get("receipt")))
		sendLog(f"{x}/25 Waiting for receipt " + str(redis.get("receipt")), False)
		if(str(redis.get("receipt")) != "b''"): break
	sent=redis.get("receipt").decode()
	redis.set("receipt", "")
	data=json.loads(sent.replace("'", "\""))
	data["msisdn"] = format_number(data["msisdn"])
	if(isInt(data["to"])):
		data["to"] = format_number("45" + data["to"])
	return data


def sendLog(logdata:str, requests:bool):
	dt = datetime.now()
	if(requests == True):
		log.info("Browser: " + request.headers.get('User-Agent') + " | " + "IP: " + request.remote_addr + " | " + "Timestamp: " + str(dt) + " | " + str(logdata))
	else:
		log.info(str(logdata))
log.info("Service started.")
def send_message(src:str, dst:str, text:str, key:str):
	if(isInt(src)):
		src=fix_number(src)
	dst=fix_number(dst)
	if(len(src) != 10 and isInt(src)):
		return "Source number is not 8 numbers long."
	if(len(dst) != 10):
		return "Destination number is not 8 numbers long."
	if(len(text) == 0 or len(text) > 140):
		return "Message either too small or too long."
	if(key != None and len(key) == 0):
		return "No key entered."
	keys=redis.lrange("sms_keys", 0, -1)
	if(str(key).encode() in keys or key == None or str(redis.lrange(key, 0, 1)) != None):
		try:
			redis.set("receipt", "")
			message = client.send_message({'from': src,'to': dst,'text': text,'type': 'unicode'})
			sendLog("From > " + str(src) + " to > "+ str(dst)[2:] + " key > " + str(key) +" text > " + str(text), True)
			if(key != None and message["messages"][0]["status"] == "0"):
				redis.lrem("sms_keys", 0, key)
			return True
		except Exception as e:
			print(e)
			traceback.print_exc()
			sendLog(f"Unknown error: {e}", True)
			return "Unknown error. Check console for more info."
	else:
		time.sleep(1)
		sendLog(f"Tried to use key that does not exist ({key})", True)
		return "Key does not exist."
@auth.verify_password
def verify_password(username, password):
	if (username, password) == ("admin", getenv("admin_pass")):
		return True
	else:
		return False

@app.route('/', methods=['GET', 'POST'])
def home(): 
	if(request.method == "POST"):
		src = request.form.get('src')
		dst = request.form.get('dst')
		key = request.form.get('key')
		text = request.form.get('text')
		message = send_message(src,dst,text,key)
		if(message == True):
			return render_template("receipt.html", data=listen_receipts(), admin=False, key=key)
		else:
			return render_template("showtext.html", title="Error",text=message)
	return render_template("index.html")	

@app.route('/admin/sms', methods=['GET', 'POST'])
@auth.login_required
def sms():
	if(request.method == "POST"):
		src = request.form.get('src')
		dst = request.form.get('dst')
		text = request.form.get('text')
		message = send_message(src,dst,text,None)
		if(message == True):
			return render_template("receipt.html", data=listen_receipts(), admin=True, key=None)
		else:	
			return render_template("showtext.html", title="Error",text=message)
	return render_template("index.html", admin=True)

@app.route('/admin/call', methods=['GET', 'POST'])
@auth.login_required
def call():
	return render_template("showtext.html", title="Error",text="Page under construction!") 



@app.route('/admin', methods=['GET', 'POST'])
@auth.login_required
def admin_panel():
	result = client.get_balance()
	if(request.method == "POST"):
		reciever = fix_number(request.form.get('reciever'))
		key = genkey(random.randint(4,16))
		redis.lpush("sms_keys", key)
		if(request.form.get('reciever')[0:2] == "X*"):
			akeys=""
			for i,x in enumerate(range(int(request.form.get('reciever')[2:]))):
				akeys+=f"<br> {i+1}: " + (genkey(random.randint(4,16)))
			return render_template("showtext.html", title=f"SMS keys: {akeys}", titleBar="SMS keys:")
		if(len(reciever) == 2):
			return render_template("showtext.html", title=f"SMS key: {key}")
		if(len(reciever) != 10):
			return render_template("showtext.html", title="Error!", text="Phone number is not 8 numbers long.")
		message = "Your one time key is: {} \nuse it here: https://sms.super02.me{}".format(key, url_for('admin_panel')) #Make sure this actually works
		try:
			redis.set("receipt", "")
			message = client.send_message({'from': "SMSService",'to': reciever,'text': message})
			sendLog(f"Generated 1 key for {reciever} ({key})", True)
			return render_template("receipt.html", data=listen_receipts(), admin=True, key=key)
		except Exception as e:
			print("Error! " + str(e))
			traceback.print_exc()
			return jsonify({"Error": "An unknown error occured. Please contact us for more info! "})
	return render_template("admin_panel.html", balance=f"{result['value']:0.2f} EUR", sms_left=str(math.floor(float(f"{result['value']:0.2f}")/0.0221)))

@app.route('/admin/sms_keys', methods=['GET', 'POST'])
@auth.login_required
def sms_keys():
	if(request.method == "POST"):
		redis.lset("sms_keys", 0, "DELETED8b57705a-f65c-11e9-802a-5aa538984bd8")
		redis.lrem("sms_keys", 1, "DELETED8b57705a-f65c-11e9-802a-5aa538984bd8")
	else:
		dropdown=""
		for i,x in enumerate(redis.lrange("sms_keys", 0, -1)):
			dropdown+=f"<a class=\"dropdown-item\">{x.decode()}</a>"
		return render_template("sms_keys.html", dropdown=dropdown)

@app.route('/email', methods=['GET', 'POST'])
@auth.login_required
def email():
	return render_template("showtext.html", title="Error!", text="Page under construction!")
	if(request.method == "POST"):
		src = request.form.get('src')
		dst = request.form.get('dst')
		key = request.form.get('key')
		text = request.form.get('text')

@app.route("/DLR-receipts", methods=['GET', 'POST'])
def DLRReceipts():
	if request.is_json:
		redis.set("receipt", str(request.get_json))
	else:
		data = dict(request.form) or dict(request.args)
		redis.set("receipt", str(data))
        
	return ('', 204)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')