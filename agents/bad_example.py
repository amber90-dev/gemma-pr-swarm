import os

API_KEY = "sk-live-1234567890abcdef"   # hard-coded secret

def get_user(db, name):
    return db.execute("SELECT * FROM users WHERE name = '" + name + "'")  # SQL injection

def run(cmd):
    os.system(cmd)   # command injection
