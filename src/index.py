from dotenv import load_dotenv
from flask import Flask, request, render_template, jsonify
from flask_httpauth import HTTPBasicAuth
from os import getenv
import plivo
import json

app = Flask(__name__)
auth = HTTPBasicAuth()
load_dotenv()

USERS = json.load(open('users.json', 'r'))

plivo_client = plivo.RestClient(getenv('auth_id'), getenv('auth_token'))

def fix_number(raw):
	raw = raw.replace(" ", "")
	raw = raw.replace("+45", "")
	return "+45{}".format(raw)

@auth.verify_password
def verify_password(username, password):
	if (username, password):
		for user in USERS.items():
			if user == (username, password):
				return True

	return False

@app.route('/', methods=['GET', 'POST'])
@auth.login_required
def root():
	if request.method == "POST":
		src = fix_number(request.form.get('src'))
		dst = fix_number(request.form.get('dst'))
		text = request.form.get('text')

		if len(src) != 11 or len(dst) != 11:
			return jsonify({"Error": "Source or Destination numbers are not 8 characters long"}), 400
		
		if len(text) == 0:
			return jsonify({"Error": "No message body"}), 400

		try:
			message = plivo_client.messages.create(src=src, dst=dst, text=text)
		except plivo.exceptions.ValidationError:
			return jsonify({"Error": "Source and Destination cannot be the same"}), 400

		message_data = plivo_client.messages.get(message.message_uuid[0])

		return render_template("result.html", msg=message_data)
		
	return render_template("index.html")

app.run(port=80, host="0.0.0.0", debug=False)