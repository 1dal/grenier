import base64
import hashlib
import getpass

from Crypto import Random
from Crypto.Cipher import AES


class AESCipher(object):
    def __init__(self, passphrase=None):
        if passphrase is None:
            passphrase = getpass.getpass("Passphrase:")
        self.key = hashlib.sha256(passphrase.encode()).digest()

    def _pad(self, s):
        length = AES.block_size - (len(s) % AES.block_size)
        return (s + bytes([length])*length)

    def _unpad(self, r):
        return r[:-r[-1]]

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = bytes(Random.new().read(AES.block_size))
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        r = cipher.decrypt(enc[AES.block_size:])
        return self._unpad(r)

    def encrypt_file(self, path):
        with  open(path, "rb") as f:
            not_encrypted = f.read()
        encrypted = self.encrypt(not_encrypted)
        with open(path, "wb") as f:
            f.write(encrypted)

    def decrypt_file(self, path):
        with open(path, "rb") as f:
            encrypted = f.read()
        not_encrypted = self.decrypt(encrypted)
        with open(path, "wb") as f:
            f.write(not_encrypted)
