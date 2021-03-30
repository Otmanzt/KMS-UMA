
from flask import Flask, render_template, request, redirect, url_for, session
from views import *
import urllib.request

app = Flask(__name__, static_url_path='/static')
app.secret_key = 'BQ2S5Idd4C'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/salir')
def salir():
    session.clear()
    return render_template('index.html')

@app.route('/iniciarSesion', methods=["GET", "POST"])
def iniciarSesion():
    datos = {}
    if request.form:
        datos = iniciar_sesion(request)

        if datos['logeado']:
            return render_template('index.html')

    return render_template('iniciar_sesion.html', datos=datos)


@app.route('/registrar', methods=["GET", "POST"])
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


@app.route('/precargar', methods=['POST', 'GET'])
def precargar():
    response = {"estado": False}

    if request.files:
        response = subir_fichero(request)

    return response


@app.route('/listar', methods=['POST', 'GET'])
def listar():
    datos = listar_ficheros()
    return render_template('listar.html', datos=datos)


@app.route('/descargar', methods=['POST', 'GET'])
def descargar():
    response = {"estado": False}

    if request.form:
        fichero = request.form['fichero']
        enctype = request.form['enctype']
        response = descargar_fichero(fichero, enctype)
    return response


@app.route('/rotar', methods=['POST', 'GET'])
def rotar():
    return render_template('rotar.html')


@app.route('/confirmarRotar', methods=['POST', 'GET'])
def confirmarRotar():
    response = {"estado": False}

    resultado = key_rotation(session['usuario'])

    if resultado:
        response['estado'] = True

    response = json.dumps(response)
    return response

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
