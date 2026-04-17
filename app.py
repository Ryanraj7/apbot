from flask import Flask, request, jsonify, render_template
from helpers import normalize_command
from match_logic import get_best_match
from db.db_intent_handler import handle_db_intent
from db.scheduled_report import generate_scheduled_reports
from email.message import EmailMessage
import threading
import smtplib
import time
import socket
import webbrowser

app = Flask(__name__)
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    user_id = request.remote_addr
    user_input_cleaned = normalize_command(user_input)

    # ✅ DB-specific logic
    if user_input_cleaned in ["track and trace", "track assets", "track my assets"]:
        try:
            from db.db_test import generate_track_and_trace_excel
            generate_track_and_trace_excel()
            return jsonify({"response": "✅ Track & Trace report has been generated. Please check the Downloads or the Reports folder."})
        except Exception as e:
            return jsonify({"response": f"❌ Failed to generate report: {str(e)}"})

    if user_input_cleaned in ["scheduled report", "generate scheduled report"]:
        try:
            summary = generate_scheduled_reports()
            return jsonify({"response": summary})
        except Exception as e:
            return jsonify({"response": f"❌ Failed to generate scheduled reports: {str(e)}"})

    if user_input_cleaned in ["picklists", "list picklists", "show picklist"]:
        response = handle_db_intent("list picklists", user_input)
        return jsonify({"response": response})

    if user_input_cleaned in ["empty locations", "list empty locations"]:
        response = handle_db_intent("list empty locations", user_input)
        return jsonify({"response": response})

    if user_input_cleaned in ["top locations", "top locations this month"]:
        response = handle_db_intent("top locations this month", user_input)
        return jsonify({"response": response})

    db_response = handle_db_intent(user_input_cleaned, user_input)
    if db_response:
        return jsonify({"response": db_response})

    # ✅ Fallback to phase 1
    phase1_response = get_best_match(user_id, user_input)
    return jsonify({"response": phase1_response})

# ✅ Email sending endpoint
@app.route("/send_email", methods=["POST"])
def send_email():
    data = request.json
    name = data.get("name")
    sender = data.get("from")
    message = data.get("message")

    try:
        email = EmailMessage()
        email['Subject'] = f"APBot Support Request from {name}"
        email['From'] = sender
        email['To'] = "team@assetpulse.com"
        email.set_content(message)

        # SMTP connection using Gmail
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login("team@assetpulse.com", "your_app_password_here")  # Replace with App Password
            smtp.send_message(email)

        return jsonify({"status": "✅ Email sent successfully!"})
    except Exception as e:
        return jsonify({"status": f"❌ Failed to send email: {str(e)}"})

# ✅ Optional: Auto-launch browser once Flask is ready
def wait_for_server_and_open():
    while True:
        try:
            with socket.create_connection(("127.0.0.1", 5000), timeout=1):
                break
        except OSError:
            time.sleep(0.5)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Thread(target=wait_for_server_and_open).start()
    app.run(debug=True)