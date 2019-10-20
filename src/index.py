from dotenv import load_dotenv
from flask import Flask, request, render_template, jsonify
from flask_httpauth import HTTPBasicAuth
from os import getenv
from redis import Redis
from random import choice
from string import digits
import plivo

app = Flask(__name__)
auth = HTTPBasicAuth()
load_dotenv()
redis = Redis().from_url(getenv("REDIS_URL"))

plivo_client = plivo.RestClient(getenv('AUTH_ID'), getenv('AUTH_TOKEN'))

def fix_number(raw: str):
	raw = raw.replace(" ", "")
	raw = raw.replace("+45", "")
	return "+45{}".format(raw)

def generate_random_key(length: int):
	return "".join(choice(digits) for _ in range(length))

def send_sms(src: str, dst: str, text: str, key=None):
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
		message = plivo_client.messages.create(src=src, dst=dst, text=text)
		if key is not None:
			redis.lrem("sms_keys", 0, key)
	except plivo.exceptions.ValidationError:
		return jsonify({"Error": "Source and Destination cannot be the same"}), 400

	redis.lpush("log", f"{src} => {dst} | Key: {key} | Text: {text}")
	message_data = plivo_client.messages.get(message.message_uuid[0])
	return render_template("result.html", msg=message_data, admin=(key is None))

@auth.verify_password
def verify_password(username, password):
	if (username, password) == ("admin", getenv("ADMIN_PASS")):
		return True

	return False

@app.route('/', methods=['GET', 'POST'])
def root():
	if request.method == "POST":
		src = fix_number(request.form.get('src'))
		dst = fix_number(request.form.get('dst'))
		key = request.form.get('key')
		text = request.form.get('text')

		return send_sms(src, dst, text, key)

	return render_template("send_sms.html")

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
				message = plivo_client.messages.create(src="+4569696969", dst=rcv, text=text)
				message_data = plivo_client.messages.get(message.message_uuid[0])
			
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
		src = fix_number(request.form.get('src'))
		dst = fix_number(request.form.get('dst'))
		text = request.form.get('text')

		return send_sms(src, dst, text)

	return render_template("send_sms.html", admin=True)

if __name__ == "__main__":
	app.run(port=8080, host="0.0.0.0", debug=False)
