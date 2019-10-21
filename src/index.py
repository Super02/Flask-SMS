from flask import Flask, request, render_template, jsonify, redirect, url_for
from flask_httpauth import HTTPBasicAuth
import nexmo
from random import choice
from string import digits
from os import getenv
from redis import Redis
from datetime import datetime

app = Flask(__name__)
auth = HTTPBasicAuth()
secret = getenv("secret")
key = getenv("key")
client = nexmo.Client(key=key, secret=secret)
redis = Redis().from_url(getenv("REDIS_URL"))

@auth.verify_password
def verify_password(username, password):
	sendLog("Someone succesfuly logged into admin panel.")
	if (username, password) == ("admin", getenv("admin_pass")):
		sendLog("Someone succesfuly logged into admin panel.")
		return True
	else:
		sendLog("Someone failed to log into admin panel.")

	return False

def sendLog(logdata:str):
	dt = datetime.now()
	redis.lpush("log", "Timestamp: " + dt + " | " + logdata)


def fix_number(raw: str):
	if(raw==None):
		return None
	raw = raw.replace(" ", "")
	raw = raw.replace("+45", "")
	return "45{}".format(raw)

def send_sms(src:str, dst:str, text:str, key=None):
	if not key is None:
		key = key.encode()
		keys = redis.lrange("sms_keys", 0, -1)
		if key not in keys:
			return jsonify({"Error": "Invalid key"}), 400
		if len(src) != 11 or len(dst) != 11:
			return jsonify({"Error": "Source or Destination numbers are not 8 characters long"}), 400
		if len(text) == 0 or len(text.encode()) > 140:
			return jsonify({"Error": "Invalid message length"}), 400
		try:
			message = client.send_message({'from': fix_number(src),'to': fix_number(dst),'text': text,})
			if key is not None:
				redis.lrem("sms_keys", 0, key)
			if(message["messages"][0]["status"] == "0"):
				sendLog("Message sent \nFrom: {}\nTo: {}\nText: {}".format(fix_number(src),fix_number(dst),text))
				print(message["messages"])
			else:
				sendLog(f"Message failed with error: {message ['messages'][0]['error-text']}")
		except Exception: #FIX LIGE OOF
			return jsonify({"Error": "Source and Destination cannot be the same"}), 400
		sendLog(f"{src} => {dst} | Key: {key} | Text: {text}")
		return render_template("result.html", msg=message, admin=(key is None))
	else:
		message =client.send_message({'from': fix_number(src),'to': fix_number(dst),'text': text,})
		if(message["messages"][0]["status"] == "0"):
			sendLog("Message sent \nFrom: {}\nTo: {}\nText: {}".format(fix_number(src),fix_number(dst),text))
			print(message["messages"])
		else:
			sendLog(f"Message failed with error: {message ['messages'][0]['error-text']}")
			print(f"Message failed with error: {message ['messages'][0]['error-text']}")


def generate_random_key(length: int):
	return "".join(choice(digits) for _ in range(length))

@app.route('/')
def home():
	return redirect(url_for("sms"), code=302)

@app.route('/admin', methods=['GET', 'POST'])
@auth.login_required
def admin_panel():
	if request.method == "POST":
		rcv = fix_number(request.form.get('rcv'))

		keys = redis.lrange("sms_keys", 0, -1)
		key = generate_random_key(4)
		while key.encode() in keys:
			key = generate_random_key(4)
			
		if (len(rcv) != 10 or len(rcv) != 10) and len(rcv) != 2:
			return jsonify({"Error": "Phone number isn't 8 numbers long."}), 400

		text = "Your one time key is: {}".format(key)

		try:
			if len(rcv) != 2:
				message =client.send_message({'from': "4569696969",'to': rcv,'text': text,})
			
			redis.lpush("sms_keys", key)
			
			if len(rcv) == 2:
				sendLog(f"Generated anonymous key ({key})")
				return jsonify({"key": key})
		except:
			return jsonify({"Error": "Unknown Error!"})

		
		sendLog(f"Generated key for {rcv} ({key})")
		return render_template("result.html", msg=message, admin=True, key=key)

	return render_template("admin.html")


@app.route('/admin/sms', methods=['GET', 'POST'])
@auth.login_required
def admin_sms():
	if request.method == "POST":
		src = request.form.get('src')
		dst = request.form.get('dst')
		text = request.form.get('text')

		send_sms(src, dst, text, None)

	return render_template("send_sms.html", admin=True)
@app.route('/sms', methods=['GET', 'POST'])
def sms():
	if request.method == "POST":
		src = request.form.get('src')
		dst = request.form.get('dst')
		text = request.form.get('text')
		key = request.form.get('key')

		send_sms(src, dst, text, key)
	return render_template("send_sms.html", admin=False)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
