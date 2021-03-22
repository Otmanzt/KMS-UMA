#https://mkyong.com/python/python-how-to-list-all-files-in-a-directory/
#https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files
#https://stackoverflow.com/questions/1035340/reading-binary-file-and-looping-over-each-byte

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import os
import shutil
import base64
import boto3

def create_cmk(description):
    """Creates a KMS Customer Master Key

    Description is used to differentiate between CMKs.
    """

    kms_client = boto3.client("kms", region_name="eu-central-1", aws_access_key_id='AKIAZ55ECWRK6Y7N4PPW', aws_secret_access_key= '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')
    response = kms_client.create_key(Description=description)

    # Return the key ID and ARN
    return response["KeyMetadata"]["KeyId"], response["KeyMetadata"]["Arn"]

def retrieve_cmk(description):
    """Retrieve an existing KMS CMK based on its description"""

    # Retrieve a list of existing CMKs
    # If more than 100 keys exist, retrieve and process them in batches
    kms_client = boto3.client('kms', region_name="eu-central-1", aws_access_key_id='AKIAZ55ECWRK6Y7N4PPW', aws_secret_access_key= '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')
    response = kms_client.list_keys()

    for cmk in response["Keys"]:
        key_info = kms_client.describe_key(KeyId=cmk["KeyArn"])
        if key_info["KeyMetadata"]["Description"] == description:
            return cmk["KeyId"], cmk["KeyArn"]

    # No matching CMK found
    return None, None

def create_data_key(cmk_id, key_spec="AES_256"):
    """Generate a data key to use when encrypting and decrypting data"""

    # Create data key
    kms_client = boto3.client("kms", region_name="eu-central-1", aws_access_key_id='AKIAZ55ECWRK6Y7N4PPW', aws_secret_access_key= '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')
    response = kms_client.generate_data_key(KeyId=cmk_id, KeySpec=key_spec)

    # Return the encrypted and plaintext data key
    return response["CiphertextBlob"], base64.b64encode(response["Plaintext"])

def encrypt_file(filename, cmk_id):
    """Encrypt JSON data using an AWS KMS CMK"""

    with open(filename, "rb") as file:
      file_contents = file.read()

    data_key_encrypted, data_key_plaintext = create_data_key(cmk_id)
    if data_key_encrypted is None:
        return

    # Encrypt the data
    f = Fernet(data_key_plaintext)
    file_contents_encrypted = f.encrypt(file_contents)

    # Write the encrypted data key and encrypted file contents together
    with open(filename + '.encrypted', 'wb') as file_encrypted:
        file_encrypted.write(len(data_key_encrypted).to_bytes(NUM_BYTES_FOR_LEN,
                                                              byteorder='big'))
        file_encrypted.write(data_key_encrypted)
        file_encrypted.write(file_contents_encrypted)

def decrypt_data_key(data_key_encrypted):
    """Decrypt an encrypted data key"""

    # Decrypt the data key
    kms_client = boto3.client("kms", region_name="eu-central-1", aws_access_key_id='AKIAZ55ECWRK6Y7N4PPW', aws_secret_access_key= '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')
    response = kms_client.decrypt(CiphertextBlob=data_key_encrypted)

    # Return plaintext base64-encoded binary data key
    return base64.b64encode((response["Plaintext"]))

def decrypt_file(filename):
    """Decrypt a file encrypted by encrypt_file()"""

    # Read the encrypted file into memory
    with open(filename + ".encrypted", "rb") as file:
      file_contents = file.read()

    # The first NUM_BYTES_FOR_LEN tells us the length of the encrypted data key
    # Bytes after that represent the encrypted file data
    data_key_encrypted_len = int.from_bytes(file_contents[:NUM_BYTES_FOR_LEN],
                                            byteorder="big") \
                             + NUM_BYTES_FOR_LEN
    data_key_encrypted = file_contents[NUM_BYTES_FOR_LEN:data_key_encrypted_len]

    # Decrypt the data key before using it
    data_key_plaintext = decrypt_data_key(data_key_encrypted)
    if data_key_plaintext is None:
        return False

    # Decrypt the rest of the file
    f = Fernet(data_key_plaintext)
    file_contents_decrypted = f.decrypt(file_contents[data_key_encrypted_len:])

    # Write the decrypted file contents
    with open(filename + '.decrypted', 'wb') as file_decrypted:
      file_decrypted.write(file_contents_decrypted)

path = '.'
path_secure = './secure/'
path_unsecure = './unsecure/'
NUM_BYTES_FOR_LEN = 4

#Clean folders
shutil.rmtree(path_secure,ignore_errors=True)
shutil.rmtree(path_unsecure,ignore_errors=True)
os.mkdir(path_secure)
os.mkdir(path_unsecure)

#List files in folder
files = []
# r=root, d=directories, f = files
for r, d, f in os.walk(path):
    for file in f:
        if '.txt' in file:
            files.append(os.path.join(r, file))

for f in files:
    print(f)

chunk_size = 256

#Use a static Master Key to protect all files.
nonce = bytes("0123456789012345",'utf-8')
key = bytes("01234567890123456789012345678901",'utf-8')

fileName= "ejemplo.txt"
description="My Customer Master Key"
key2,test2 = create_cmk(description)
print(key2)

encrypt_file(fileName, key2)
decrypt_file(fileName, key2)

#Ferment doesn't implemt the update pattern, so I am using a stream cipher instead.
algorithm = algorithms.ChaCha20(key, nonce)
cipher = Cipher(algorithm, mode=None, backend=default_backend())
encryptor = cipher.encryptor()

#PUT: Encrypt a file into secure folder
file_to_put= "ejemplo.txt"
with open(file_to_put, "rb") as source, open(path_secure+file_to_put, "wb+") as sink:
    byte = source.read(chunk_size)
    while byte:
        sink.write(encryptor.update(byte))
        # Do stuff with byte.
        byte = source.read(chunk_size)
    source.close()
    sink.close()

decryptor = cipher.decryptor()

#GET: Encrypt a file into secure folder
file_to_get= "ejemplo.txt"
with open(path_secure+file_to_get, "rb") as source, open(path_unsecure+file_to_get, "wb+") as sink:
    byte = source.read(chunk_size)
    while byte:
        sink.write(decryptor.update(byte))
        # Do stuff with byte.
        byte = source.read(chunk_size)
    source.close()
    sink.close()