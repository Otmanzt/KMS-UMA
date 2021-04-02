import pymongo as pymongo
import hashlib
import random
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import os, binascii
from backports.pbkdf2 import pbkdf2_hmac

client = pymongo.MongoClient("mongodb+srv://spea:grupodetres@cluster0.uscnp.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")
db = client['ServerFiles']
coleccionUsuarios = db['Usuarios']
coleccionFicheros = db['Ficheros']


def insertar_usuario(correo, password):
    hashed_password = hashlib.new("sha1", password.encode())

    #Crea la key_client para guardarla con el usuario a crear.
    hexadecimal = "0123456789abcdef"
    saltChar=""
    for i in range(32):
        saltChar=saltChar+random.choice(hexadecimal)
    salt = binascii.unhexlify(saltChar)

    passwordTmp = password.encode("utf8")
    key = pbkdf2_hmac("sha256", passwordTmp, salt, 50000, 32)

    usuario = {"correo": correo, "password": hashed_password.hexdigest(), "key": binascii.hexlify(key)}
    resultado = coleccionUsuarios.insert_one(usuario)
    return resultado


def buscar_usuario(correo):
    resultado = coleccionUsuarios.find_one({"correo": correo})
    return resultado


def comprobar_usuario(correo, password):
    hashed_password = hashlib.new("sha1", password.encode())
    resultado = coleccionUsuarios.find_one({"correo": correo, "password": hashed_password.hexdigest()})

    if resultado is not None:
        resultado = True

    return resultado


def buscar_ficheros_usuario(correo):
    resultado = coleccionFicheros.find({"$or" :[{"client": correo}, {"compartido": correo}]}, {"_id": 1, "nombre": 1, "fecha_subida": 1, "tipo_enc":1})
    return resultado
