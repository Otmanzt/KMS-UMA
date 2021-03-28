#https://mkyong.com/python/python-how-to-list-all-files-in-a-directory/
#https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files
#https://stackoverflow.com/questions/1035340/reading-binary-file-and-looping-over-each-byte

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import os
import shutil
import base64
import pymongo as pymongo

from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import os, binascii
from backports.pbkdf2 import pbkdf2_hmac
from Crypto.Cipher import AES

client = pymongo.MongoClient("mongodb+srv://spea:grupodetres@cluster0.uscnp.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")
db = client['ServerFiles']
coleccionUsuarios = db['Usuarios']
coleccionFicheros = db['Ficheros']
nonce = bytes("0123456789012345",'utf-8')

def convert_key(shared_key):
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'handshake data',
    ).derive(shared_key)

    key = base64.urlsafe_b64encode(derived_key)

    return key

def encrypt_data_key(key_client, filename, encrypt_option):

    salt = binascii.unhexlify('aaef2d3f4d77ac66e9c5a6c3d8f921d1')
    password = filename.encode("utf8")
    key = pbkdf2_hmac("sha256", password, salt, 50000, 32)

    if encrypt_option == 0:
        f = Fernet(convert_key(key_client))
        return f.encrypt(key), key
    else:
        key_aes = convert_key(key_client)
        key_aes = key_aes[1:33]

        cipher = AES.new(key_aes, AES.MODE_GCM, nonce=nonce)
        encrypted_message = cipher.encrypt(key) 
        return encrypted_message, key

def encrypt_file(client_name, fichero, encrypt_option):
    filename = fichero.filename
    upload_path = 'upload/' + filename
    fichero.save(upload_path)
    encrypted_path = 'encrypted/' + client_name
    key_client = coleccionUsuarios.find_one({"correo": client_name})['key']

    with open(upload_path, "rb") as file:
        file_contents = file.read()

    data_key_encrypted, data_key_plaintext = encrypt_data_key(key_client, upload_path, encrypt_option)

    if encrypt_option == 0:
        f = Fernet(convert_key(data_key_plaintext))
        file_contents_encrypted = f.encrypt(file_contents)
    else:
        key_aes = convert_key(data_key_plaintext)
        key_aes = key_aes[1:33]

        cipher = AES.new(key_aes, AES.MODE_GCM, nonce=nonce)
        file_contents_encrypted = cipher.encrypt(file_contents) 

    os.makedirs(encrypted_path, exist_ok=True)

    with open(encrypted_path + '/' + filename, 'wb') as file_encrypted:
        file_encrypted.write(file_contents_encrypted)
    
    #DESCOMENTAR PARA LA FASE FINAL
    os.remove(upload_path)

    coleccionFicheros.delete_many({"path": encrypted_path + '/' + filename})
    fichero = {"client": client_name, "datakey": data_key_encrypted, "path": encrypted_path + '/' + filename}
    coleccionFicheros.insert_one(fichero)

def decrypt_data_key(data_key_encrypted, key_client, encrypt_option):

    if encrypt_option == 0:
        f = Fernet(convert_key(key_client))
        return f.decrypt(data_key_encrypted)
    else:
        key_aes = convert_key(key_client)
        key_aes = key_aes[1:33]

        cipher = AES.new(key_aes, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt(data_key_encrypted)

def decrypt_file(client_name, filename, encrypt_option):

    encrypted_path = 'encrypted/' + client_name
    decrypted_path = 'download/' + client_name
    key_client = coleccionUsuarios.find_one({"correo": client_name})['key']
    data_key_encrypted = coleccionFicheros.find_one({"path": encrypted_path + "/" + filename})['datakey']

    with open(encrypted_path + '/' + filename, "rb") as file:
        file_contents = file.read()

    data_key_plaintext = decrypt_data_key(data_key_encrypted, key_client, encrypt_option)

    if encrypt_option == 0:
        f = Fernet(convert_key(data_key_plaintext))
        file_contents_decrypted = f.decrypt(file_contents)
    else:
        key_aes = convert_key(data_key_plaintext)
        key_aes = key_aes[1:33]

        cipher = AES.new(key_aes, AES.MODE_GCM, nonce=nonce)
        file_contents_decrypted = cipher.decrypt(file_contents)

    os.makedirs(decrypted_path, exist_ok=True)

    with open(decrypted_path + '/' + filename, 'wb') as file_decrypted:
        file_decrypted.write(file_contents_decrypted)

def key_rotation(client_name, encrypt_option):

    oldKeyClient = coleccionUsuarios.find_one({"correo": client_name})['key']
    password = coleccionUsuarios.find_one({"correo": client_name})['password']

    salt = binascii.unhexlify('aaef2d3f4d77ac66e9c5a6c3d8f921d1')
    passwordTmp = password.encode("utf8")
    newKeyClient = pbkdf2_hmac("sha256", passwordTmp, salt, 50000, 32)

    coleccionUsuarios.update_one({"correo": client_name},{"$set": {"key": newKeyClient}})

    encrypted_path = 'encrypted/' + client_name
    keyrotation_path = 'keyrotation/' + client_name

    for filename in os.listdir(encrypted_path):

        data_key_encrypted = coleccionFicheros.find_one({"path": encrypted_path + "/" + filename})['datakey']

        with open(encrypted_path + '/' + filename, "rb") as file:
            file_contents = file.read()
      
        data_key_plaintext = decrypt_data_key(data_key_encrypted, oldKeyClient, encrypt_option)

        if encrypt_option == 0:
            f = Fernet(convert_key(data_key_plaintext))
            file_contents_decrypted = f.decrypt(file_contents)
        else:
            key_aes = convert_key(data_key_plaintext)
            key_aes = key_aes[1:33]

            cipher = AES.new(key_aes, AES.MODE_GCM, nonce=nonce)
            file_contents_decrypted = cipher.decrypt(file_contents)
        
        os.makedirs(keyrotation_path, exist_ok=True)

        with open(keyrotation_path + '/' + filename, 'wb') as file_decrypted:
            file_decrypted.write(file_contents_decrypted)

        os.remove(encrypted_path + '/' + filename)

        with open(keyrotation_path + '/' + filename, "rb") as file:
            file_contents = file.read()
        
        data_key_encrypted, data_key_plaintext = encrypt_data_key(newKeyClient, keyrotation_path, encrypt_option)

        if encrypt_option == 0:
            f = Fernet(convert_key(data_key_plaintext))
            file_contents_encrypted = f.encrypt(file_contents)
        else:
            key_aes = convert_key(data_key_plaintext)
            key_aes = key_aes[1:33]

            cipher = AES.new(key_aes, AES.MODE_GCM, nonce=nonce)
            file_contents_encrypted = cipher.encrypt(file_contents) 

        with open(encrypted_path + '/' + filename, 'wb') as file_encrypted:
            file_encrypted.write(file_contents_encrypted)
        
        os.remove(keyrotation_path + '/' + filename)

        coleccionFicheros.update_one({"path": encrypted_path + "/" + filename},{"$set": {"datakey": data_key_encrypted}})

'''
fileName= "ejemplo.txt"
nameClient = "testflowww@yahoo.com"

encrypt_file(nameClient, fileName, 1)
key_rotation(nameClient, 1)
decrypt_file(nameClient, fileName, 1)

nameClient2 = "test2"
keyClient2 = create_key_client(nameClient2)
keyFile2 = encrypt_file(keyClient2, nameClient2, fileName)

decrypt_file(keyClient,keyFile,nameClient,fileName)
decrypt_file(keyClient2,keyFile2,nameClient2,fileName)

newKeyClient = create_key_client(nameClient)

key_rotation(keyClient, newKeyClient, keyFile, nameClient, fileName)
'''