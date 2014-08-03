import nacl.utils
from nacl.public import Box, PrivateKey, PublicKey


def generate_keypair():
    """Generates a key pair"""
    secret = PrivateKey.generate()
    public = secret.public_key
    return str(secret).encode('hex'), str(public).encode('hex')


def encrypt_text(text, secret_key, rcpt_public_key):
    """Encrypts a text
    """
    secret_key = PrivateKey(secret_key.decode('hex'))
    rcpt_public_key = PublicKey(rcpt_public_key.decode('hex'))
    box = Box(secret_key, rcpt_public_key)
    return box.encrypt(text, nacl.utils.random(Box.NONCE_SIZE))


def decrypt_text(text, secret_key, sender_public_key):
    """Decrypts a text
    """
    secret_key = PrivateKey(secret_key.decode('hex'))
    sender_public_key = PublicKey(sender_public_key.decode('hex'))
    box = Box(secret_key, sender_public_key)
    return box.decrypt(text)


if __name__ == '__main__':
    skalice, pbalice = generate_keypair()
    skbob, pbbob = generate_keypair()
    encrypted = encrypt_text('1234', skalice, pbbob)
    assert '1234' == decrypt_text(encrypted, skbob, pbalice)
