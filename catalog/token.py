import cryptography.fernet
import datetime
import json
from pathlib import Path
from os import path

P = Path(__file__).parent.absolute()
SECRET_FILE = P / 'secret.txt'

if not path.exists(SECRET_FILE):
    with open(SECRET_FILE, 'w') as f:
        secret_key = cryptography.fernet.Fernet.generate_key()
        f.write(secret_key.decode())
with open(SECRET_FILE, 'r') as f:
    SECRET = f.read().encode()
cryptofunc = cryptography.fernet.Fernet(SECRET)


def now():
    return datetime.datetime.now().timestamp()


class Token:
    def __init__(self, username, expiration_time):
        self.username = username
        self.expiration_time = expiration_time

    def is_expired(self):
        return self.expiration_time < now()

    @staticmethod
    def serialize(token):
        json_obj = {
            'username': token.username,
            'expiration_time': token.expiration_time,
        }
        json_str = json.dumps(json_obj)
        crypt_token = cryptofunc.encrypt(bytes(json_str, 'utf-8')).decode('utf-8')
        return crypt_token

    @staticmethod
    def deserialize(crypt_token):
        json_str = cryptofunc.decrypt(bytes(crypt_token, 'utf-8'))
        json_obj = json.loads(json_str)
        token = Token(json_obj['username'], json_obj['expiration_time'])
        return token

    @staticmethod
    def generate(username):
        expiration_time = now() + datetime.timedelta(weeks=4).total_seconds()
        token = Token(username, expiration_time)
        return token
