#https://mkyong.com/python/python-how-to-list-all-files-in-a-directory/
#https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files
#https://stackoverflow.com/questions/1035340/reading-binary-file-and-looping-over-each-byte

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import os
import shutil
import base64

from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import os, binascii
from backports.pbkdf2 import pbkdf2_hmac

def convert_key(shared_key):
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'handshake data',
    ).derive(shared_key)

    key = base64.urlsafe_b64encode(derived_key)

    return key

def create_key_client(password):

    salt = binascii.unhexlify('aaef2d3f4d77ac66e9c5a6c3d8f921d1')
    password = password.encode("utf8")
    key = pbkdf2_hmac("sha256", password, salt, 50000, 32)
    
    return binascii.hexlify(key)

def get_key_client(client):
    return None

def encrypt_data_key(filename, key_client):

    salt = binascii.unhexlify('aaef2d3f4d77ac66e9c5a6c3d8f921d1')
    password = filename.encode("utf8")
    key = pbkdf2_hmac("sha256", password, salt, 50000, 32)

    f = Fernet(convert_key(key_client))
    return f.encrypt(key), key

def encrypt_file(filename, key_client):

    with open(filename, "rb") as file:
      file_contents = file.read()

    data_key_encrypted, data_key_plaintext = encrypt_data_key(filename, key_client)

    f = Fernet(convert_key(data_key_plaintext))
    file_contents_encrypted = f.encrypt(file_contents)

    with open(filename + '.encrypted', 'wb') as file_encrypted:
        file_encrypted.write(file_contents_encrypted)

    return data_key_encrypted

def decrypt_data_key(data_key_encrypted, key_client):

    f = Fernet(convert_key(key_client))
    return f.decrypt(data_key_encrypted)

def decrypt_file(filename, data_key_encrypted, key_client):

    with open(filename + ".encrypted", "rb") as file:
      file_contents = file.read()

    data_key_plaintext = decrypt_data_key(data_key_encrypted, key_client)

    f = Fernet(convert_key(data_key_plaintext))
    file_contents_decrypted = f.decrypt(file_contents)

    with open(filename + '.decrypted', 'wb') as file_decrypted:
      file_decrypted.write(file_contents_decrypted)

def change_files_with_new_keys(oldKeyClient, newKeyClient, data_key_encrypted, filename):

    decrypt_file(filename, data_key_encrypted, oldKeyClient)
    data_key_encryptionNew=encrypt_file(filename, newKeyClient)

    os.remove(filename + '.decrypted')
    return data_key_encryptionNew

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

fileNameMiguel= "ejemplo.txt"

keyClient = create_key_client("test")
keyFile = encrypt_file(fileNameMiguel, keyClient)

keyClient2 = create_key_client("test")
newKeyFile = change_files_with_new_keys(keyClient,keyClient2,keyFile,fileNameMiguel)
decrypt_file(fileNameMiguel,newKeyFile,keyClient2)

#key2,test2 = create_cmk("miguel")
#key3,test3 = create_cmk("alex")

#keyFileMiguel = encrypt_file(fileNameMiguel, key2)
#keyFileAlex = encrypt_file(fileNameAlex, key3)

#decrypt_file(fileNameMiguel, keyFileMiguel, key2)
#decrypt_file(fileNameAlex, keyFileAlex, key3)

#decrypt_file(fileName, keyFile)

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