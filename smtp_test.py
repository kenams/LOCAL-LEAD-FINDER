import os
import smtplib
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("SMTP_HOST")
port = int(os.getenv("SMTP_PORT", "587"))
username = os.getenv("SMTP_USERNAME")
password = os.getenv("SMTP_PASSWORD")

print("HOST:", host)
print("PORT:", port)
print("USERNAME:", username)
print("PASSWORD PRESENT:", bool(password))
print("PASSWORD LENGTH:", len(password) if password else 0)

server = smtplib.SMTP(host, port)
server.starttls()
server.login(username, password)
print("SMTP LOGIN OK")
server.quit()