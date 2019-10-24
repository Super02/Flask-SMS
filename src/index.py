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

def isInt(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False
def genkey(length:int):
	x = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(length))
	return x
def fix_number(number:str):
	if(number == None):
		return None
	number = number.replace(" ", "").replace("+45", "")
	return "45" + number
def listen_receipts():
	for x in range(25):
		time.sleep(1)
		print(f"{x}/25 Waiting for receipt " + str(redis.get("receipt")))
		if(str(redis.get("receipt")) != "b''"): break
	sent=redis.get("receipt").decode()
	redis.set("receipt", "")
	return json.loads(sent.replace("'", "\""))


def sendLog(logdata:str): #Fix pls
	dt = datetime.now()
	redis.lpush("log", "Browser: " + request.headers.get('User-Agent') + " | " + "IP: " + request.remote_addr + " | " + "Timestamp: " + str(dt) + " | " + logdata)

def send_message(src:str, dst:str, text:str, key:str):
	src=fix_number(src)
	dst=fix_number(dst)
	if(len(src) != 10):
		return "Source number is not 8 numbers long."
	if(len(dst) != 10):
		return "Destination number is not 8 numbers long."
	if(len(text) == 0 or len(text) > 140):
		return "Message either too small or too long."
	if(len(key) == 0):
		return "No key entered."
	keys=redis.lrange("sms_keys", 0, -1)
	if(key.encode() in keys):
		try:
			message = client.send_message({'from': src,'to': dst,'text': text})
			if(key != None):
				redis.lrem("sms_keys", 0, key)
			return True
		except Exception as e:
			print(e)
			traceback.print_exc()
			return "Unknown error. Check console for more info."
	else:
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
			special=True
			if(isInt(src.replace(" ", ""))):
				special=False
			return render_template("receipt.html", data=listen_receipts(), admin=True, key=key, special=special)
		else:
			return render_template("showtext.html", title="Error",text=message)
	return render_template("index.html")	

@app.route('/admin', methods=['GET', 'POST'])
@auth.login_required
def admin_panel():
	if(request.method == "POST"):
		reciever = fix_number(request.form.get('reciever'))
		keys = redis.lrange("sms_keys", 0, -1)
		key = genkey(random.randint(4,16))
		while key.encode() in keys:
			key = genkey(random.randint(4,16))
		redis.lpush("sms_keys", key)
		if(len(reciever) == 2):
			return render_template("showtext.html", title=f"SMS key: {key}")
		if(len(reciever) != 10):
			return render_template("showtext.html", title="Error!", text="Phone number is not 8 numbers long.")
		message = "Your one time key is: {} \nuse it here: {}".format(key, url_for('admin_panel')) #Make sure this actually works
		try:
			message = client.send_message({'from': "SMSService",'to': reciever,'text': message})
			sendLog(f"Generated 1 key for {reciever} ({key})") # Might wanna check how it works with sendlog
			return render_template("receipt.html", data=listen_receipts(), admin=True, key=key, special=True)
		except Exception as e:
			print("Error! " + str(e))
			traceback.print_exc()
			return jsonify({"Error": "An unknown error occured. Please contact us for more info! "})
	return render_template("admin_panel.html")
@app.route('/admin/sms_keys', methods=['GET', 'POST'])
@auth.login_required
def sms_keys():
	return render_template("showtext.html", title="Error!", text="This page is under construction.")
	if(request.method == "POST"):
		redis.lset("sms_keys", 0, "DELETED8b57705a-f65c-11e9-802a-5aa538984bd8")
		redis.lrem("sms_keys", 1, "DELETED8b57705a-f65c-11e9-802a-5aa538984bd8")
	else:
		dropdown=""
		for i,x in enumerate(redis.lrange("sms_keys", 0, -1)):
			dropdown+=f"<a class=\"dropdown-item\" href=\"#{i}\">{x.decode()}</a>"
		return render_template("sms_keys.html", dropdown=dropdown)

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
