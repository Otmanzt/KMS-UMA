import pymongo as pymongo
import hashlib

client = pymongo.MongoClient("mongodb+srv://spea:grupodetres@cluster0.uscnp.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")
db = client['ServerFiles']
coleccion = db['Usuarios']


def insertar_usuario(correo, password):
    hashed_password = hashlib.new("sha1", password.encode())
    usuario = {"correo": correo, "password": hashed_password.hexdigest()}
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
