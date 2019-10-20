from flask import Flask, request, render_template, jsonify
from flask_httpauth import HTTPBasicAuth
import nexmo
from random import choice
from string import digits
from os import getenv
from redis import Redis

app = Flask(__name__)
auth = HTTPBasicAuth()
secret = "94LMmzLUGFsbKyTr"
key = "16fecadf"
client = nexmo.Client(key=key, secret=secret)
redis = Redis().from_url("redis://h:p39e65e7459f3b7aab4ef0dbbfe27f1849467120a8e75cad91643ab080dafb23c@ec2-34-246-123-190.eu-west-1.compute.amazonaws.com:26389")

@auth.verify_password
def verify_password(username, password):
	if (username, password) == ("admin", "6969"):
		return True

	return False

def fix_number(raw: str):
	raw = raw.replace(" ", "")
	raw = raw.replace("+45", "")
	return "{}".format(raw)

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
			message =client.send_message({'from': fix_number(src),'to': "45"+fix_number(dst),'text': text,})
			if key is not None:
				redis.lrem("sms_keys", 0, key)
		except Exception: #FIX LIGE OOF
			return jsonify({"Error": "Source and Destination cannot be the same"}), 400
		redis.lpush("log", f"{src} => {dst} | Key: {key} | Text: {text}")
		return render_template("result.html", msg=message, admin=(key is None))
	else:
		message =client.send_message({'from': fix_number(src),'to': "45"+fix_number(dst),'text': text,})
		if(message["messages"][0]["status"] == "0"):
			redis.lpush("log", "Message sent \nFrom: {}\nTo: {}\nText: {}".format(fix_number(src),fix_number(dst),text))
		else:
			redis.lpush("log", f"Message failed with error: {message ['messages'][0]['error-text']}")
			print(f"Message failed with error: {message ['messages'][0]['error-text']}")


def generate_random_key(length: int):
	return "".join(choice(digits) for _ in range(length))

@app.route('/admin', methods=['GET', 'POST'])
@auth.login_required
def admin_panel():
	if request.method == "POST":
		rcv = fix_number(request.form.get('rcv'))

		keys = redis.lrange("sms_keys", 0, -1)
		key = generate_random_key(4)
		while key.encode() in keys:
			key = generate_random_key(4)
			
		if (len(rcv) != 11 or len(rcv) != 11) and len(rcv) != 3:
			return jsonify({"Error": "Phone number isn't 8 numbers long."}), 400

		text = "Your one time key is: {}".format(key)

		try:
			if len(rcv) != 3:
				message =client.send_message({'from': "69696969",'to': "45"+fix_number(rcv),'text': text,})
			
			redis.lpush("sms_keys", key)
			
			if len(rcv) == 3:
				redis.lpush("log", f"Generated anonymous key ({key})")
				return jsonify({"key": key})
		except:
			return jsonify({"Error": "Unknown Error!"})

		redis.lpush("log", f"Generated key for {rcv} ({key})")
		return render_template("result.html", msg=message_data, admin=True)

	return render_template("admin.html")


@app.route('/admin/sms', methods=['GET', 'POST'])
@auth.login_required
def admin_sms():
	if request.method == "POST":
		src = request.form.get('src')
		dst = fix_number(request.form.get('dst'))
		text = request.form.get('text')

		send_sms(src, dst, text, None)

	return render_template("send_sms.html", admin=True)
@app.route('/sms', methods=['GET', 'POST'])
def sms():
	if request.method == "GET":
		src = fix_number(request.form.get('src'))
		dst = fix_number(request.form.get('dst'))
		text = request.form.get('text')
		key = request.form.get('key')

		send_sms(src, dst, text, key)

	return render_template("send_sms.html", admin=False)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')