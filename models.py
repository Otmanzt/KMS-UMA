import pymongo as pymongo
import hashlib
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import os, binascii
from backports.pbkdf2 import pbkdf2_hmac

client = pymongo.MongoClient("mongodb+srv://spea:grupodetres@cluster0.uscnp.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")
db = client['ServerFiles']
coleccion = db['Usuarios']


def insertar_usuario(correo, password):
    hashed_password = hashlib.new("sha1", password.encode())

    #Crea la key_client para guardarla con el usuario a crear.
    salt = binascii.unhexlify('aaef2d3f4d77ac66e9c5a6c3d8f921d1')
    passwordTmp = password.encode("utf8")
    key = pbkdf2_hmac("sha256", passwordTmp, salt, 50000, 32)

    usuario = {"correo": correo, "password": hashed_password.hexdigest(), "key": binascii.hexlify(key)}
    resultado = coleccion.insert_one(usuario)
    return resultado


def buscar_usuario(correo):
    resultado = coleccion.find_one({"correo": correo})
    return resultado


def comprobar_usuario(correo, password):
    hashed_password = hashlib.new("sha1", password.encode())
    resultado = coleccion.find_one({"correo": correo, "password": hashed_password.hexdigest()})

    if resultado is not None:
        resultado = True

    return resultado
