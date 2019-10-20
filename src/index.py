from flask import Flask
from flask import Flask, request, render_template, jsonify
from flask_httpauth import HTTPBasicAuth
from twilio.rest import Client 
from twilio.base.exceptions import TwilioRestException
from random import choice
from string import digits
from os import getenv

app = Flask(__name__)
auth = HTTPBasicAuth()
account_sid = getenv("account_sid")
auth_token = getenv('auth_token')
client = Client(account_sid, auth_token)
keys=["1234"]

@auth.verify_password
def verify_password(username, password):
	if (username, password) == ("admin", getenv("admin_pass")):
		return True

	return False

def fix_number(raw: str):
	raw = raw.replace(" ", "")
	raw = raw.replace("+45", "")
	return "+45{}".format(raw)
def check_key(key: str):
	return False
	if(key in keys): return True

def send_sms(src:str, dst:str, text:str, key):
	if(key != None):
		if(check_key(key) != True): return "Error" 
		else: keys.remove(key)
	message = client.messages \
	.create(
		body=text,
		from_="a" + src.replace(" ", "")[3:],
		to=fix_number(dst)
	)
	print(message.sid)

def generate_random_key(length: int):
	return "".join(choice(digits) for _ in range(length))



@app.route('/admin/sms', methods=['GET', 'POST'])
@auth.login_required
def admin_sms():
	if request.method == "POST":
		src = fix_number(request.form.get('src'))
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