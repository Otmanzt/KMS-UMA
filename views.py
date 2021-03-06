from models import *
from flask import session
from kms import *
import json
from bson import ObjectId

# Funcion para coger los datos de registro y crearlo en la base de datos de MongoDB
def registrar_usuario(request):
    datos = {'ok': True, "msg": "", "insertado": False}
    correo = request.form['correo']
    cont1 = request.form['cont1']
    cont2 = request.form['cont2']

    if cont1 == cont2:
        resultado = buscar_usuario(correo)

        if resultado is None:
            insertar_usuario(correo, cont1)
            datos['insertado'] = True
        else:
            datos['ok'] = False
            datos['msg'] = "Ese correo ya esta registrado"
    else:
        datos['ok'] = False
        datos['msg'] = "Contraseñas no coinciden"

    return datos


# Funcion para iniciar sesion
def iniciar_sesion(request):
    datos = {'correo': None, 'ok': False, 'msg': "", "logeado": False}
    correo= request.form['correo']
    cont1 = request.form['pass']

    resultado = comprobar_usuario(correo, cont1)
    if resultado:
        datos['logeado'] = True
        session["usuario"] = correo
    else:
        datos['ok'] = False
        datos['msg'] = "Contraseña incorrecta"

    return datos

# Se lee el tipo de ENC seleccionada en el formulario y el fichero a subir. Despues se le pasa a la funcion encrypt_file del KMS
def subir_fichero(request):
    fichero = request.files['fichero']
    opcionEnc = request.form["opcionEnc"]
    
    # Si el campo compartido esta vacio, no hay comparticion
    if request.form['compartido'] == "":
        encrypt_file(session["usuario"], fichero, int(opcionEnc), "")
        response = {
        "estado": True,
        "fichero": fichero.filename,
        "opcionEnc": request.form["opcionEnc"]
        }
    else:   
        # Si no esta vaciio, se comprueba en la base de datos si existe el usuario con el que se quiere compartir     
        if coleccionUsuarios.find_one({"correo": request.form['compartido']}):
        # EXISTE
           # Llamamos a encriptar el fichero con los dos usuarios
           encrypt_file(session["usuario"], fichero, int(opcionEnc), request.form['compartido']) 
           response = {
            "estado": True,
            "fichero": fichero.filename,
            "opcionEnc": request.form["opcionEnc"]
            } 
        
        # NO EXISTE   
        else:
            # Devolvemos response 0 para que salte la alerta de error
            response=0                     

    response = json.dumps(response)
    return response


def listar_ficheros():
    lista = buscar_ficheros_usuario(session["usuario"])
    return lista


def descargar_fichero(fichero, enctype):
    ruta = decrypt_file(session["usuario"], fichero)

    response = {
        "enlace": ruta
    }

    response = json.dumps(response)
    return response

def borrar_fichero_BD(id):
    # Convertimos el id a object id para poder buscar en MongoDB por Id
    id = ObjectId(id)
    # Extraemos el path para luego efectuar un borrado seguro
    path = coleccionFicheros.find_one({"_id": id})['path']
    # Eliminamos el fichero de la BD
    coleccionFicheros.delete_one({"_id": id})    
    return path
