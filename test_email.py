import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

host = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
port = int(os.getenv('EMAIL_PORT', 587))
user = os.getenv('EMAIL_HOST_USER')
password = os.getenv('EMAIL_HOST_PASSWORD')

print(f"Testing SMTP: {host}:{port} with user {user}")

try:
    server = smtplib.SMTP(host, port)
    server.starttls()
    server.login(user, password)
    print("Login successful!")
    
    msg = MIMEText("Hello, this is a test from Telvex.")
    msg['Subject'] = 'Teivex SMTP Test'
    msg['From'] = user
    msg['To'] = user
    
    server.sendmail(user, [user], msg.as_string())
    print("Test email sent successully!")
    server.quit()
except Exception as e:
    print(f"FAILED: {e}")
