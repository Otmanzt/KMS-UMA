
from flask import Flask, render_template, request, redirect, url_for, session
from views import *
import urllib.request
from secure_delete import secure_delete

app = Flask(__name__, static_url_path='/static')
app.secret_key = 'BQ2S5Idd4C'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/salir') #Se liberan las variables de sesion para cerrar la sesion del cliente
def salir():
    session.clear()
    return render_template('index.html')

@app.route('/iniciarSesion', methods=["GET", "POST"]) # Se llama a iniciar sesion en views.py
def iniciarSesion():
    datos = {}
    if request.form:
        datos = iniciar_sesion(request)

        if datos['logeado']:
            return render_template('index.html')

    return render_template('iniciar_sesion.html', datos=datos)


@app.route('/registrar', methods=["GET", "POST"]) # Se recogen los datos del formulario de registro y se envia la request a registrar_usuario. Si se completa el registro se redirige a index.
def registrar():
    datos = {}

    if request.form:
        datos = registrar_usuario(request)

        if datos['insertado']:
            return render_template('index.html')

    return render_template('registrar.html', datos=datos)


@app.route('/agregar', methods=['POST', 'GET'])
def agregar():
    return render_template('agregar.html')


@app.route('/precargar', methods=['POST', 'GET']) #Evento AJAX para coger el fichero y hacer las pertinentes operaciones en el KMS
def precargar():
    response = {"estado": False}
 
    if request.files:
        response = subir_fichero(request)
    return response


@app.route('/listar', methods=['POST', 'GET'])
def listar():
    datos = listar_ficheros()
    return render_template('listar.html', datos=datos)


@app.route('/descargar', methods=['POST', 'GET']) # Se hace una peticion AJAX para desencriptar el fichero correspondiente y se devuelve el enlace para mostrarlo por pantalla
def descargar():
    response = {"estado": False}

    if request.form:
        fichero = request.form['fichero']
        enctype = request.form['enctype']
        response = descargar_fichero(fichero, enctype)
    return response

@app.route('/borradoSeguro/<id>', methods=['POST', 'GET'])
def borrar(id):
    # Extraemos el path del fichero guardado en la BD
    path = borrar_fichero_BD(id)
    # Usando la libreria secure_delete efectuamos el borrado seguro del fichero
    secure_delete.secure_random_seed_init()
    secure_delete.secure_delete(path)
    # Volvemos a calcular la lista de ficheros del usuario
    datos = listar_ficheros()
    return render_template('listar.html', datos=datos)


@app.route('/rotar', methods=['POST', 'GET'])
def rotar():
    return render_template('rotar.html')


@app.route('/confirmarRotar', methods=['POST', 'GET']) # Se llama a la funcion de key_rotation del KMS directamente pasando el ID del usuario
def confirmarRotar():
    response = {"estado": False}

    resultado = key_rotation(session['usuario'])

    if resultado:
        response['estado'] = True

    response = json.dumps(response)
    return response

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
