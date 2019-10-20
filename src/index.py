from flask import Flask, request, render_template, jsonify
from flask_httpauth import HTTPBasicAuth
from twilio.rest import Client 
from twilio.base.exceptions import TwilioRestException
from random import choice
from string import digits
from os import getenv
from redis import Redis

app = Flask(__name__)
auth = HTTPBasicAuth()
account_sid = getenv("account_sid")
auth_token = getenv('auth_token')
client = Client(account_sid, auth_token)
redis = Redis().from_url(getenv("REDIS_URL"))

@auth.verify_password
def verify_password(username, password):
	if (username, password) == ("admin", getenv("admin_pass")):
		return True

	return False

def fix_number(raw: str):
	raw = raw.replace(" ", "")
	raw = raw.replace("+45", "")
	return "+45{}".format(raw)

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
			message = client.messages.create(body=text, from_="a31688852", to=fix_number(dst))
			print(message.sid)
			if key is not None:
				redis.lrem("sms_keys", 0, key)
		except TwilioRestException:
			return jsonify({"Error": "Source and Destination cannot be the same"}), 400
		redis.lpush("log", f"{src} => {dst} | Key: {key} | Text: {text}")
		return render_template("result.html", msg=message, admin=(key is None))


def generate_random_key(length: int):
	return "".join(choice(digits) for _ in range(length))



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
	if request.method == "POST":
		src = fix_number(request.form.get('src'))
		dst = fix_number(request.form.get('dst'))
		text = request.form.get('text')
		key = request.form.get('key')

		send_sms(src, dst, text, key)

	return render_template("send_sms.html", admin=False)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')