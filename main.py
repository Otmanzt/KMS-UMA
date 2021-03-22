
from flask import Flask, render_template, request, redirect, url_for, session
from views import *

app = Flask(__name__, static_url_path='/static')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/iniciarSesion', methods=["GET", "POST"])
def iniciarSesion():
    datos = iniciar_sesion(request)
    return render_template('iniciar_sesion.html', datos=datos)


@app.route('/registrar', methods=["GET", "POST"])
def registrar():
    datos = registrar_usuario(request)
    return render_template('registrar.html', datos=datos)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
