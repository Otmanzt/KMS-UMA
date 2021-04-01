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
from datetime import datetime
import hashlib

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
    elif encrypt_option == 1:
        key_aes = convert_key(key_client)
        key_aes = key_aes[1:33]

        cipher = AES.new(key_aes, AES.MODE_GCM, nonce=nonce)
        encrypted_message = cipher.encrypt(key) 
        return encrypted_message, key

def encrypt_file(client_name, fichero, encrypt_option, compartido):
    if compartido != "":
        key_client = create_shared_key(client_name, compartido, fichero.filename)
    else:
        key_client = coleccionUsuarios.find_one({"correo": client_name})['key']
    filename = fichero.filename
    upload_path = 'upload/' + filename
    fichero.save(upload_path)
    encrypted_path = 'encrypted/' + client_name
    encrypted_path2 = 'encrypted/' + compartido

    with open(upload_path, "rb") as file:
        file_contents = file.read()

    data_key_encrypted, data_key_plaintext = encrypt_data_key(key_client, upload_path, encrypt_option)

    if encrypt_option == 0:
        f = Fernet(convert_key(data_key_plaintext))
        file_contents_encrypted = f.encrypt(file_contents)
    elif encrypt_option == 1:
        key_aes = convert_key(data_key_plaintext)
        key_aes = key_aes[1:33]

        cipher = AES.new(key_aes, AES.MODE_GCM, nonce=nonce)
        file_contents_encrypted = cipher.encrypt(file_contents) 

    os.makedirs(encrypted_path, exist_ok=True)
    if compartido != "":
        os.makedirs(encrypted_path2, exist_ok=True)

    with open(encrypted_path + '/' + filename, 'wb') as file_encrypted:
        file_encrypted.write(file_contents_encrypted)
        
    if compartido != "":
        with open(encrypted_path2 + '/' + filename, 'wb') as file_encrypted:
            file_encrypted.write(file_contents_encrypted) 
           
    os.remove(upload_path)
    fecha_subida = datetime.today()

    coleccionFicheros.delete_many({"path": encrypted_path + '/' + filename})
    if compartido != "":
        coleccionFicheros.delete_many({"path": encrypted_path2 + '/' + filename})
        fileToUpload = {"client": client_name, "datakey": data_key_encrypted, "path": encrypted_path + '/' + filename,"path2": encrypted_path2 + '/' + filename, "fecha_subida": fecha_subida, "nombre": filename, "tipo_enc": encrypt_option, "compartido": compartido}
    else:
        fileToUpload = {"client": client_name, "datakey": data_key_encrypted, "path": encrypted_path + '/' + filename, "fecha_subida": fecha_subida, "nombre": filename, "tipo_enc": encrypt_option}
    coleccionFicheros.insert_one(fileToUpload)

def decrypt_data_key(data_key_encrypted, key_client, encrypt_option):

    if encrypt_option == 0:
        f = Fernet(convert_key(key_client))
        return f.decrypt(data_key_encrypted)
    elif encrypt_option == 1:
        key_aes = convert_key(key_client)
        key_aes = key_aes[1:33]

        cipher = AES.new(key_aes, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt(data_key_encrypted)

def decrypt_file(client_name, filename):
    encrypted_path = 'encrypted/' + client_name
    decrypted_path = 'download/' + client_name
    identificador = filename.replace('.', '_')
    if coleccionFicheros.find_one({"path": encrypted_path + "/" + filename}) is None:
       key_client = coleccionUsuarios.find_one({"correo": client_name})['shared_key'+identificador] 
       data_key_encrypted = coleccionFicheros.find_one({"path2": encrypted_path + "/" + filename})['datakey'] 
       encrypt_option = coleccionFicheros.find_one({"path2": encrypted_path + "/" + filename})['tipo_enc']
    elif coleccionFicheros.find_one({"path": encrypted_path + "/" + filename}) is not None and coleccionFicheros.find_one({"path": encrypted_path + "/" + filename}).get('compartido'):
        key_client = coleccionUsuarios.find_one({"correo": client_name})['shared_key' + identificador]
        data_key_encrypted = coleccionFicheros.find_one({"path": encrypted_path + "/" + filename})['datakey']
        encrypt_option = coleccionFicheros.find_one({"path": encrypted_path + "/" + filename})['tipo_enc']
    else:
        key_client = coleccionUsuarios.find_one({"correo": client_name})['key'] 
        data_key_encrypted = coleccionFicheros.find_one({"path": encrypted_path + "/" + filename})['datakey']
        encrypt_option = coleccionFicheros.find_one({"path": encrypted_path + "/" + filename})['tipo_enc']

    with open(encrypted_path + '/' + filename, "rb") as file:
        file_contents = file.read()

    data_key_plaintext = decrypt_data_key(data_key_encrypted, key_client, encrypt_option)

    if encrypt_option == 0:
        f = Fernet(convert_key(data_key_plaintext))
        file_contents_decrypted = f.decrypt(file_contents)
    elif encrypt_option == 1:
        key_aes = convert_key(data_key_plaintext)
        key_aes = key_aes[1:33]

        cipher = AES.new(key_aes, AES.MODE_GCM, nonce=nonce)
        file_contents_decrypted = cipher.decrypt(file_contents)

    os.makedirs(decrypted_path, exist_ok=True)

    with open(decrypted_path + '/' + filename, 'wb') as file_decrypted:
        file_decrypted.write(file_contents_decrypted)

    ruta = decrypted_path + '/' + filename

    return ruta

def key_rotation(client_name):

    oldKeyClient = coleccionUsuarios.find_one({"correo": client_name})['key']
    password = coleccionUsuarios.find_one({"correo": client_name})['password']

    salt = binascii.unhexlify('aaef2d3f4d77ac66e9c5a6c3d8f921d1')
    passwordTmp = password.encode("utf8")
    newKeyClient = pbkdf2_hmac("sha256", passwordTmp, salt, 50000, 32)

    coleccionUsuarios.update_one({"correo": client_name},{"$set": {"key": newKeyClient}})

    encrypted_path = 'encrypted/' + client_name
    keyrotation_path = 'keyrotation/' + client_name
    file_contents_decrypted = None

    for filename in os.listdir(encrypted_path):

        data_key_encrypted = coleccionFicheros.find_one({"path": encrypted_path + "/" + filename})['datakey']
        encrypt_option = coleccionFicheros.find_one({"path": encrypted_path + "/" + filename})['tipo_enc']

        with open(encrypted_path + '/' + filename, "rb") as file:
            file_contents = file.read()
      
        data_key_plaintext = decrypt_data_key(data_key_encrypted, oldKeyClient, encrypt_option)

        if encrypt_option == 0:
            f = Fernet(convert_key(data_key_plaintext))
            file_contents_decrypted = f.decrypt(file_contents)
        elif encrypt_option == 1:
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

        resultado = coleccionFicheros.update_one({"path": encrypted_path + "/" + filename},{"$set": {"datakey": data_key_encrypted}})

        return resultado
    
def create_shared_key(client_name, compartido, filename):
    password1 = key_client = coleccionUsuarios.find_one({"correo": client_name})['password']
    password2 = key_client = coleccionUsuarios.find_one({"correo": compartido})['password']
    
    password_shared = password1 + password2
    
    hashed_password = hashlib.new("sha1", password_shared.encode())

    #Crea la key_client para guardarla con el usuario a crear.
    salt = binascii.unhexlify('aaef2d3f4d77ac66e9c5a6c3d8f921d1')
    passwordTmp = password_shared.encode("utf8")
    key = pbkdf2_hmac("sha256", passwordTmp, salt, 50000, 32)
    
    filename = filename.replace('.', '_')
    
    identificador = "shared_key" + filename

    dato = {"$set": {identificador: binascii.hexlify(key)}}
    coleccionUsuarios.update_one({"correo": client_name}, dato)
    coleccionUsuarios.update_one({"correo": compartido}, dato)
    return binascii.hexlify(key)        