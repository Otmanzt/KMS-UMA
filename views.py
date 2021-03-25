from models import *
from flask import session


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
