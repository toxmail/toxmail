import nacl.utils
from nacl.public import Box, PrivateKey


def generate_keypair():
    """Generates a key pair"""
    secret = PrivateKey.generate()
    public = secret.public_key
    return secret, public


def encrypt_text(text, secret_key, rcpt_public_key):
    """Encrypts a text
    """
    box = Box(secret_key, rcpt_public_key)
    return box.encrypt(text, nacl.utils.random(Box.NONCE_SIZE))


def decrypt_text(text, secret_key, sender_public_key):
    """Decrypts a text
    """
    box = Box(secret_key, sender_public_key)
    return box.decrypt(text)


if __name__ == '__main__':
    skalice, pbalice = generate_keypair()
    skbob, pbbob = generate_keypair()

    encrypted = encrypt_text('1234', skalice, pbbob)
    assert '1234' == decrypt_text(encrypted, skbob, pbalice)
