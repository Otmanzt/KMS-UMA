import base64
import boto3

def encrypt(session, secret, alias):
    client = session.client('kms')
    ciphertext = client.encrypt(
        KeyId=alias,
        Plaintext=bytes(secret),
    )
    return base64.b64encode(ciphertext["CiphertextBlob"])


def decrypt(session, secret):
    client = session.client('kms')
    plaintext = client.decrypt(
        CiphertextBlob=bytes(base64.b64decode(secret))
    )
    return plaintext["Plaintext"]


session = boto3.session.Session()
print(encrypt(session, 'something', 'alias/MyKeyAlias'))
print(decrypt(session, 'AQECAINdoimaasydoasidDASD5asd45'))