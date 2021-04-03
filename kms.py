from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import os
import shutil
import base64
import random
import pymongo as pymongo
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import os, binascii
from backports.pbkdf2 import pbkdf2_hmac
from Crypto.Cipher import AES
from datetime import datetime
import hashlib

#Variables que necesitamos para conectarnos a la BBDD y acceder a ela.
client = pymongo.MongoClient("mongodb+srv://spea:grupodetres@cluster0.uscnp.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")
db = client['ServerFiles']
coleccionUsuarios = db['Usuarios']
coleccionFicheros = db['Ficheros']
nonce = bytes("0123456789012345",'utf-8')

#Se encarga de convertir la clave en otro formato ya que dependiendo de donde la usemos la necesitamos de una manera u otra.
def convert_key(shared_key):
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'handshake data',
    ).derive(shared_key)

    key = base64.urlsafe_b64encode(derived_key)

    return key

#Crea la clave del archivo para encriptarlo
def encrypt_data_key(key_client, filename, encrypt_option):

    hexadecimal = "0123456789abcdef"
    saltChar=""
    for i in range(32):
        saltChar=saltChar+random.choice(hexadecimal)
    salt = binascii.unhexlify(saltChar)
    
    #Creamos una data key con la contraseña del usuario
    password = filename.encode("utf8")
    key = pbkdf2_hmac("sha256", password, salt, 50000, 32)

    #Dependiendo del formato de encriptación, usamos fernet o AHEAD para encriptar la clave del archivo con la clave del cliente
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
    # Si compartido no esta vacio, el fichero esta compartido entre algunos usuarios
    if compartido != "":
        # Creamos una nueva key compartida para dicho fichero
        key_client = create_shared_key(client_name, compartido, fichero.filename)
    else:
        # No hay comparticion, se extrae la key del usuario guardada en BD
        key_client = coleccionUsuarios.find_one({"correo": client_name})['key']
    
    # Extraemos el nombre del fichero para crear la nueva ruta donde va a estar encriptado    
    filename = fichero.filename
    upload_path = 'upload/' + filename
    fichero.save(upload_path)
    encrypted_path = 'encrypted/' + client_name
    # Creamos una segunda ruta para el caso de fichero compartido
    encrypted_path2 = 'encrypted/' + compartido
    
    # Leemos el contenido del fichero
    with open(upload_path, "rb") as file:
        file_contents = file.read()
            
    #Obtenemos la clave del archivo.
    data_key_encrypted, data_key_plaintext = encrypt_data_key(key_client, upload_path, encrypt_option)

    #Encriptamos archivo con el formato de encriptación elegido.
    if encrypt_option == 0:
        f = Fernet(convert_key(data_key_plaintext))
        file_contents_encrypted = f.encrypt(file_contents)
    elif encrypt_option == 1:
        key_aes = convert_key(data_key_plaintext)
        key_aes = key_aes[1:33]

        cipher = AES.new(key_aes, AES.MODE_GCM, nonce=nonce)
        file_contents_encrypted = cipher.encrypt(file_contents) 

    #Guardamos el archivo en el directorio del usuario.
    os.makedirs(encrypted_path, exist_ok=True)
    if compartido != "":
        os.makedirs(encrypted_path2, exist_ok=True)

    with open(encrypted_path + '/' + filename, 'wb') as file_encrypted:
        file_encrypted.write(file_contents_encrypted)
    
    # Si hay comparticion efectuamos la encriptacion en la segunda ruta creada    
    if compartido != "":
        with open(encrypted_path2 + '/' + filename, 'wb') as file_encrypted:
            file_encrypted.write(file_contents_encrypted) 
    
    # Borramos el archivo de la carpeta upload       
    os.remove(upload_path)
    fecha_subida = datetime.today()
    
    # Borramos todos los posibles ficheros con la misma ruta para evitar conflictos
    coleccionFicheros.delete_many({"path": encrypted_path + '/' + filename})
    
    # Si existe comparticion, borramos tambien los posibles ficheros con la segunda ruta
    if compartido != "":
        coleccionFicheros.delete_many({"path": encrypted_path2 + '/' + filename})
        # Dato a insertar con la ruta, data_key, fecha de subida, nombre del fichero, tipo de encriptacion
        # Introducimos la segunda ruta en el dato a insertar y un campo de con quien se esta compartiendo
        fileToUpload = {"client": client_name, "datakey": data_key_encrypted, "path": encrypted_path + '/' + filename,"path2": encrypted_path2 + '/' + filename, "fecha_subida": fecha_subida, "nombre": filename, "tipo_enc": encrypt_option, "compartido": compartido}
    else:
        # Dato a insertar con la ruta, data_key, fecha de subida, nombre del fichero, tipo de encriptacion
        fileToUpload = {"client": client_name, "datakey": data_key_encrypted, "path": encrypted_path + '/' + filename, "fecha_subida": fecha_subida, "nombre": filename, "tipo_enc": encrypt_option}
    
    # Insercion en la BD del dato anterior
    coleccionFicheros.insert_one(fileToUpload)

#Devuelve la data key desencriptada sabiendo la key del cliente, la data key encriptada y el método de desencriptación.
def decrypt_data_key(data_key_encrypted, key_client, encrypt_option):

    if encrypt_option == 0:
        f = Fernet(convert_key(key_client))
        return f.decrypt(data_key_encrypted)
    elif encrypt_option == 1:
        key_aes = convert_key(key_client)
        key_aes = key_aes[1:33]

        cipher = AES.new(key_aes, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt(data_key_encrypted)

#Desencripta un fichero.
def decrypt_file(client_name, filename):
    encrypted_path = 'encrypted/' + client_name
    decrypted_path = 'download/' + client_name
    
    # Volvemos a reemplazar el punto por _ puesto que asi se guarda en la base de datos las claves de los ficheros compartidos
    identificador = filename.replace('.', '_')
    
    # Si no existe el path con el nombre del usuario, es el usuario con el que esta compartido el fichero
    if coleccionFicheros.find_one({"path": encrypted_path + "/" + filename}) is None:
       # Sacamos la shared_key del fichero
       key_client = coleccionUsuarios.find_one({"correo": client_name})['shared_key'+identificador] 
       # Extraemos el data_key_ecrypted usando el path2 ya que no es el usuario principal
       data_key_encrypted = coleccionFicheros.find_one({"path2": encrypted_path + "/" + filename})['datakey'] 
       # Finalmente extraemos el tipo de encriptacion
       encrypt_option = coleccionFicheros.find_one({"path2": encrypted_path + "/" + filename})['tipo_enc']
    
    # Si existe el path con el nombre del usuario y el campo compartido del fichero existe, es el usuario principal   
    elif coleccionFicheros.find_one({"path": encrypted_path + "/" + filename}) is not None and coleccionFicheros.find_one({"path": encrypted_path + "/" + filename}).get('compartido'):
        # Extraemos la shared_key del fichero
        key_client = coleccionUsuarios.find_one({"correo": client_name})['shared_key' + identificador]
        # Extraemos el data_key_encrypted ahora usando el path puesto que es el usuario principal
        data_key_encrypted = coleccionFicheros.find_one({"path": encrypted_path + "/" + filename})['datakey']
        # Finalmente extraemos el tipo de encriptacion
        encrypt_option = coleccionFicheros.find_one({"path": encrypted_path + "/" + filename})['tipo_enc']
    
    # En otro caso el fichero no esta compartido
    else:
        # Extraemos la key del cliente
        key_client = coleccionUsuarios.find_one({"correo": client_name})['key'] 
        # Extraemos el data_key_ecrypted
        data_key_encrypted = coleccionFicheros.find_one({"path": encrypted_path + "/" + filename})['datakey']
        # Finalmente extraemos el tipo de encriptacion
        encrypt_option = coleccionFicheros.find_one({"path": encrypted_path + "/" + filename})['tipo_enc']
    
    # Leemos el contenido del fichero encriptado
    with open(encrypted_path + '/' + filename, "rb") as file:
        file_contents = file.read()

    #Obtenemos la data key para desencriptarlo.
    data_key_plaintext = decrypt_data_key(data_key_encrypted, key_client, encrypt_option)

    #Desencriptamos el fichero con la clave.
    if encrypt_option == 0:
        f = Fernet(convert_key(data_key_plaintext))
        file_contents_decrypted = f.decrypt(file_contents)
    elif encrypt_option == 1:
        key_aes = convert_key(data_key_plaintext)
        key_aes = key_aes[1:33]

        cipher = AES.new(key_aes, AES.MODE_GCM, nonce=nonce)
        file_contents_decrypted = cipher.decrypt(file_contents)

    #Creamos la ruta para guardar el fichero desencriptado
    os.makedirs(decrypted_path, exist_ok=True)

    #Guarda el archivo desencriptado.
    with open(decrypted_path + '/' + filename, 'wb') as file_decrypted:
        file_decrypted.write(file_contents_decrypted)

    ruta = decrypted_path + '/' + filename

    #Devolvemos la ruta en la que se ha guardado el archivo desencriptado.
    return ruta

#Crea una key client nueva para un cliente y cambiar las data keys de los ficheros con la nueva key client.
def key_rotation(client_name):

    #Obtenemos la password y la key client antigua del cliente
    oldKeyClient = coleccionUsuarios.find_one({"correo": client_name})['key']
    password = coleccionUsuarios.find_one({"correo": client_name})['password']

    #Creamos una key client nueva aleatoria
    hexadecimal = "0123456789abcdef"
    saltChar=""
    for i in range(32):
        saltChar=saltChar+random.choice(hexadecimal)
    salt = binascii.unhexlify(saltChar)

    passwordTmp = password.encode("utf8")
    newKeyClient = pbkdf2_hmac("sha256", passwordTmp, salt, 50000, 32)

    #Guardamos la clave del cliente nueva.
    coleccionUsuarios.update_one({"correo": client_name},{"$set": {"key": newKeyClient}})

    encrypted_path = 'encrypted/' + client_name
    keyrotation_path = 'keyrotation/' + client_name
    file_contents_decrypted = None

    #Por cada fichero encriptado del usuario...
    for filename in os.listdir(encrypted_path):

        #Obtenemos la data key encriptada actual y la opcion de encriptación usada.
        data_key_encrypted = coleccionFicheros.find_one({"path": encrypted_path + "/" + filename})['datakey']
        encrypt_option = coleccionFicheros.find_one({"path": encrypted_path + "/" + filename})['tipo_enc']

        #Abrimos el archivo
        with open(encrypted_path + '/' + filename, "rb") as file:
            file_contents = file.read()
      
        #Desencriptamos la data key.
        data_key_plaintext = decrypt_data_key(data_key_encrypted, oldKeyClient, encrypt_option)

        #Desencriptamos el archivo
        if encrypt_option == 0:
            f = Fernet(convert_key(data_key_plaintext))
            file_contents_decrypted = f.decrypt(file_contents)
        elif encrypt_option == 1:
            key_aes = convert_key(data_key_plaintext)
            key_aes = key_aes[1:33]

            cipher = AES.new(key_aes, AES.MODE_GCM, nonce=nonce)
            file_contents_decrypted = cipher.decrypt(file_contents)
        
        #Lo guardamos en un directorio especifico para hacer la rotación de clave
        os.makedirs(keyrotation_path, exist_ok=True)

        #Guardamos el archivo desencriptado en el directorio especifico.
        with open(keyrotation_path + '/' + filename, 'wb') as file_decrypted:
            file_decrypted.write(file_contents_decrypted)

        #Borramos el archivo encriptado con la data key antigua.
        os.remove(encrypted_path + '/' + filename)

        #Abrimos el archivo desencriptado
        with open(keyrotation_path + '/' + filename, "rb") as file:
            file_contents = file.read()
        
        #Creamos una data key nueva con la client key nueva.
        data_key_encrypted, data_key_plaintext = encrypt_data_key(newKeyClient, keyrotation_path, encrypt_option)

        #Encriptamos el archivo con el mismo método que tenía antes, pero con la data key nueva.
        if encrypt_option == 0:
            f = Fernet(convert_key(data_key_plaintext))
            file_contents_encrypted = f.encrypt(file_contents)
        else:
            key_aes = convert_key(data_key_plaintext)
            key_aes = key_aes[1:33]

            cipher = AES.new(key_aes, AES.MODE_GCM, nonce=nonce)
            file_contents_encrypted = cipher.encrypt(file_contents) 

        #Guardamos el archivo en la carpeta de ficheros encriptados del usuario
        with open(encrypted_path + '/' + filename, 'wb') as file_encrypted:
            file_encrypted.write(file_contents_encrypted)
        
        #Borramos el archivo del directorio especifico para hacer la rotación.
        os.remove(keyrotation_path + '/' + filename)

        #Actualizamos la data key nueva encriptada con la client key nueva en la base de datos.
        resultado = coleccionFicheros.update_one({"path": encrypted_path + "/" + filename},{"$set": {"datakey": data_key_encrypted}})

        return resultado
    
def create_shared_key(client_name, compartido, filename):
    # Extraemos las dos passwords de los dos usuarios que van a compartir el fichero
    password1 = key_client = coleccionUsuarios.find_one({"correo": client_name})['password']
    password2 = key_client = coleccionUsuarios.find_one({"correo": compartido})['password']
    
    # Concatenamos las password
    password_shared = password1 + password2
    
    # Calculamos su hash
    hashed_password = hashlib.new("sha1", password_shared.encode())

    # Crea la key_client compartida para guardarla en los dos usuarios.
    hexadecimal = "0123456789abcdef"
    saltChar=""
    for i in range(32):
        saltChar=saltChar+random.choice(hexadecimal)
    salt = binascii.unhexlify(saltChar)

    passwordTmp = password_shared.encode("utf8")
    key = pbkdf2_hmac("sha256", passwordTmp, salt, 50000, 32)
    
    # Reemplazamos los puntos por _ para diferenciar las shared_key de cada fichero
    filename = filename.replace('.', '_')
    
    identificador = "shared_key" + filename
    
    # Actualizamos los dos usuarios introduciendo la nueva clave compartida de dicho fichero
    dato = {"$set": {identificador: binascii.hexlify(key)}}
    coleccionUsuarios.update_one({"correo": client_name}, dato)
    coleccionUsuarios.update_one({"correo": compartido}, dato)
    return binascii.hexlify(key)        