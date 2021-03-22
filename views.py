
# Funcion para coger los datos de registro y crearlo en la base de datos de MongoDB
def registrar_usuario(request):
    datos = {'correo': None, 'ok': False}
    if request.form:
        datos['correo'] = request.form['correo']
        cont1 = request.form['cont1']
        cont2 = request.form['cont2']

        if cont1 == cont2:
            datos['ok'] = True

    return datos


# Funcion para iniciar sesion
def iniciar_sesion(request):
    datos = {'correo': None, 'ok': False}
    if request.form:
        datos['correo'] = request.form['correo']
        cont1 = request.form['cont1']
        cont2 = request.form['cont2']

        if cont1 == cont2:
            datos['ok'] = True

    return datos
