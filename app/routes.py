#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import app
from flask import render_template, request, url_for, redirect, session
from flask import make_response
import json
import os
import sys
import re
import random
import hashlib
from datetime import date

catalogue = None


# Función para leer el catalogo y no repetir código
def leer_catalogo():
    global catalogue
    catalogue_data = open(os.path.join(app.root_path, 'catalogue/catalogue.json'), encoding="utf-8").read()
    catalogue = json.loads(catalogue_data)


# Funcion para obtener todos los detalles de la película, a partir del titulo
def obtener_detalles_pelicula(film):
    global catalogue
    if catalogue is None:
        leer_catalogo()

    for element in catalogue['peliculas']:
        if element['titulo'].replace(' ', '_') == film:
            return element
    return None


# Reads the data file from the given path into a dictionary and returns it
def data_to_dict(path):
    dict = {}
    f = open(path, 'r')
    for line in f.readlines():
        words = line.split(' ')
        dict[words[0]] = words[2][:-1]
    f.close()
    return dict


def update_historial_pedidos():
    global catalogue
    if catalogue is None:
        leer_catalogo()

    usersfolder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'usuarios')
    personalhistorial = os.path.join(usersfolder, session['usuario'], 'historial.json')
    f = open(personalhistorial, "r+")
    lista_ids = []
    # En esta lista almacenamos la cantidad de películas de cada elemento
    lista_cantidad = []
    for film in session['peliculas_carrito']:
        lista_ids.append(film['id'])
        lista_cantidad.append(film['cantidad'])

    historial_dict = {}

    # Si el archivo esta vacio, empezamos a escribir desde 0 el fichero .json
    if os.stat(personalhistorial).st_size == 0:
        lista_diccionarios = []
        lista_diccionarios.append({'ids': lista_ids, 'cantidad': lista_cantidad, 'fecha': str(date.today())})
        historial_dict['pedidos'] = lista_diccionarios
        f.write(json.dumps(historial_dict, indent=4))
        f.close()

    # Si el archivo ya tiene contenido, leemos le json y añadimos peliculas con su fecha
    else:
        historial_data = open(personalhistorial, encoding="utf-8").read()
        historial_dict = json.loads(historial_data)

        historial_dict['pedidos'].append({'ids': lista_ids, 'cantidad': lista_cantidad, 'fecha': str(date.today())})
        f.write(json.dumps(historial_dict, indent=4))
        f.close()


@app.route('/', methods=["GET", "POST"])
@app.route('/index/', methods=["GET", "POST"])
def index():
    sys.stderr.write(url_for('static', filename='master.css'))

    global catalogue
    if catalogue is None:
        leer_catalogo()

    # Guardar una lista con las categorias por las que se puede filtrar una peli
    categories = []
    filtered_list = []

    for element in catalogue['peliculas']:
        if element['categoria'] not in categories:
            categories.append(element['categoria'])

    categories.sort()

    if request.method == 'POST':
        busqueda = request.form['busqueda']
        for element in catalogue['peliculas']:
            if re.search(busqueda, element['titulo']) is not None:
                filtered_list.append(element)
        return render_template('index.html', catalogo=filtered_list, categories=categories)

    filter = request.args.get("filter")
    if filter is not None:
        for element in catalogue['peliculas']:
            if element['categoria'].replace(' ', '_') == filter:
                filtered_list.append(element)
        return render_template('index.html', catalogo=filtered_list, categories=categories)

    return render_template('index.html', catalogo=catalogue['peliculas'], categories=categories)
    # return render_template('index.html', title = "Home", movies=catalogue['peliculas'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    # doc sobre request object en http://flask.pocoo.org/docs/1.0/api/#incoming-request-data

    # Si nos llaman con metodo get, significa que se acaba de registrar
    if request.args.get("username"):
        # Vaciamos la url de la sesion, para volver al index cuando iniciamos sesion
        session.pop('url_origen', None)
        session.modified = True

        # Le dejamos en la página de inicio de sesión para que acceda
        login_text = "Ahora puedes iniciar sesion con tu usuario " + request.args.get("username")
        context_dict = {'text': login_text}
        return render_template('login.html', title="Sign In", message=context_dict)

    # Si acaban de pulsar el boton de iniciar sesion
    if request.method == 'POST':
        usersfolder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'usuarios')
        personalfolder = os.path.join(usersfolder, request.form['Username'], 'data.dat')

        # Comprobamos si el usuario existe
        if not os.path.exists(usersfolder) or not os.path.exists(personalfolder):
            err_text = "No existe el usuario " + request.form['Username']
            context_dict = {'text': err_text}

            return render_template('login.html', title="Sign In", message=context_dict)

        else:
            # dictionary with the data.dat file
            dict = data_to_dict(personalfolder)

            if dict['Username'] == request.form['Username'] and dict['Password'] == hashlib.md5(
                    str(request.form['Password']).encode('utf-8')).hexdigest():
                session['usuario'] = request.form['Username']
                session['saldo'] = dict['Saldo']
                session.modified = True

                if 'url_origen' in session.keys():
                    # Si estas en login por voluntad propia, al iniciar sesion te devuelve al index
                    if session['url_origen'] is not "http://0.0.0.0:5001/login":
                        resp = make_response(redirect(session['url_origen']))
                        resp.set_cookie('username', request.form['Username'])
                        return resp
                resp = make_response(redirect(url_for('index')))
                resp.set_cookie('username', request.form['Username'])
                return resp

            else:
                err_text = "Contraseña incorrecta para el usuario " + request.form['Username']
                context_dict = {'text': err_text}
                return render_template('login.html', title="Sign In", message=context_dict)
    else:
        session['url_origen'] = request.referrer
        session.modified = True

    return render_template('login.html', title="Sign In")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        usersfolder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'usuarios')
        if not os.path.exists(usersfolder):
            os.mkdir(usersfolder)

        personalfolder = os.path.join(usersfolder, request.form['Username'])
        if os.path.exists(personalfolder):
            err_text = "El usuario " + request.form['Username'] + " ya existe. Elija otro nombre de usuario"
            context_dict = {'text': err_text}
            return render_template('register.html', err=context_dict)

        else:
            # Creamos la carpeta del usuario, y los ficheros data.dat e historial.json
            os.mkdir(personalfolder)
            personaldata = os.path.join(personalfolder, 'data.dat')
            personalhistory = os.path.join(personalfolder, 'historial.json')

            f = open(personalhistory, "w+")
            f.close()

            f = open(personaldata, "w+")
            for key in request.form:
                if key == 'Password' or key == 'Passwordrpt':
                    f.write("{} : {}\n".format(key, hashlib.md5(str(request.form[key]).encode('utf-8')).hexdigest()))
                else:
                    f.write("{} : {}\n".format(key, request.form[key]))

            # asignamos un saldo aleatorio:
            f.write("Saldo : {}\n".format(random.randint(1, 101)))
            f.close()
            return redirect(url_for('login', username=request.form['Username']))

    else:
        return render_template('register.html')


@app.route('/catalogo', methods=['GET', 'POST'])
def catalogo():
    return render_template('catalogo.html')


@app.route('/carrito', methods=['GET', 'POST'])
def carrito():
    lista_peliculas = None
    precio_total = 0

    if 'peliculas_carrito' in session.keys():
        lista_peliculas = session['peliculas_carrito']

        # Multiplicamos el precio de la película por la cantidad de peliculas que hay en el carrito de ese tipo
        for pelicula in lista_peliculas:
            precio_total += pelicula['precio'] * pelicula['cantidad']

    return render_template('carrito.html', lista_peliculas=lista_peliculas, precio=round(precio_total, 2))


@app.route('/pedidos', methods=['GET', 'POST'])
def pedidos():
    global catalogue

    # Si el usuario ha iniciado sesion, empezamos a cargar el historial
    if 'usuario' in session.keys():
        if catalogue is None:
            leer_catalogo()

        usersfolder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'usuarios')
        personal_folder = os.path.join(usersfolder, session['usuario'])
        historial_file = os.path.join(personal_folder, "historial.json")

        # Si el archivo esta vacio, di que no hay pedidos
        if os.stat(historial_file).st_size == 0:
            err_text = session['usuario'] + ", todavia no ha realizado ningun pedido"
            context_dict = {'text': err_text}
            return render_template('pedidos.html', title="Pedidos", message=context_dict)

        historial_pedidos = open(historial_file, encoding="utf-8").read()
        pedidos = json.loads(historial_pedidos)

        lista_total = []
        for line in pedidos['pedidos']:
            lista = []
            precio_pedido = 0
            num_peliculas = 0

            lista.append(line['fecha'])

            # añade el número de artículos del pedido (incluyendo el número de articulos que están repetidos)

            # Vamos mirando cada id, pero tenemos que tener en cuenta cúantos se han pedido de ese id
            i = 0
            for id in line['ids']:
                for elemento_catalogo in catalogue['peliculas']:
                    if elemento_catalogo['id'] == id:
                        precio_pedido += float(elemento_catalogo['precio']) * float(line['cantidad'][i])
                        num_peliculas += int(line['cantidad'][i])

                        elemento_catalogo['cantidad'] = line['cantidad'][i]
                        lista.append(elemento_catalogo)
                i += 1

            # añade el número de peliculas del pedido
            lista.append(len(lista) - 1)

            # añade el precio total del pedido
            lista.append(precio_pedido)
            # total_pelis = 0
            # for cantidad in line['cantidad']:
            #     total_pelis += int(cantidad)
            lista.append(num_peliculas)

            # Tendo una lista con la fecha del pedido, las peliculas de ese pedido, cuántas son y cual es su precio total
            lista_total.append(lista)

        # Lista de listas de pedidos
        return render_template('pedidos.html', title="Pedidos", lista_total=lista_total)

    # Si no has iniciado sesion, te muestra un mensaje de que tienes que iniciar sesion
    else:
        err_text = "Debes iniciar sesión para ver tu historial de pedidos"
        context_dict = {'text': err_text}
        return render_template('pedidos.html', title="Pedidos", message=context_dict)


@app.route('/about', methods=['GET', 'POST'])
def about():
    return render_template('about.html', title="About")


@app.route('/terms', methods=['GET', 'POST'])
def terms():
    return render_template('terms.html',  title="Routes")


@app.route('/detalles_pelicula/<film>', methods=['GET', 'POST'])
def detalles_pelicula(film):
    global catalogue
    if catalogue is None:
        leer_catalogo()

    film_details = obtener_detalles_pelicula(film)

    return render_template('detalles_pelicula.html', title=film_details['titulo'], pelicula=film_details)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('usuario', None)
    session.pop('peliculas_carrito', None)

    return redirect(url_for('index'))


@app.route('/aniadir_carrito/<film>', methods=['GET', 'POST'])
def aniadir_carrito(film):
    global catalogue
    if catalogue is None:
        leer_catalogo()

    # En film_details tengo la película que se ha añadido al carrito
    film_details = obtener_detalles_pelicula(film)

    if 'peliculas_carrito' not in session.keys():
        film_details['cantidad'] = 1
        lista_compra = [film_details]
        session['peliculas_carrito'] = lista_compra

    else:
        # No podemos utilizar 'not in' porque la cantidad de peliculas va cambiando
        found = 0
        for pelicula in session['peliculas_carrito']:
                if pelicula['titulo'].replace(' ', '_') == film:
                    found = 1
        if found == 0:
            # Aniadimos una película en el carrito
            film_details['cantidad'] = 1
            session['peliculas_carrito'].append(film_details)
        else:
            # La pelicula esta dentro por lo que actualizamos su cantidad
            actualizar_carrito(film, 1)

    # Vuelvo a la página de detalles de la pelicula
    session.modified = True
    return redirect(request.referrer)


@app.route('/actualizar_carrito/<film>/<modificacion>', methods=['GET', 'POST'])
def actualizar_carrito(film, modificacion):
    # 1 significa sumar, 0 significa restar
    global catalogue

    # Si intentan llamar a la pagina con un número que no sea ni 0 ni 1, da error
    if int(modificacion) != 0 and int(modificacion) != 1:
        return redirect(url_for('carrito'))

    # Hacemos un bucle para ver sobre que pelicula se desea modificar la cantidad
    # y una vez encontrada, la modificamos

    i = 0
    for pelicula in session['peliculas_carrito']:
        if pelicula['titulo'].replace(' ', '_') == film:

            if int(modificacion) == 0:
                cantidad = int(session['peliculas_carrito'][i]['cantidad']) - 1
                if cantidad <= 0:
                    cantidad = 1
            elif int(modificacion) == 1:
                cantidad = int(session['peliculas_carrito'][i]['cantidad']) + 1

            session['peliculas_carrito'][i]['cantidad'] = cantidad
            session.modified = True
        i += 1

    return redirect(url_for('carrito'))


@app.route('/eliminar_carrito/<film>', methods=['GET', 'POST'])
def eliminar_carrito(film):
    global catalogue
    if catalogue is None:
        leer_catalogo()

    # En film_details tengo la película que se quiere borrar del carrito
    film_details = obtener_detalles_pelicula(film)

    # Quiero borrar la pelicula de la sesion. No lo puedo hacer directamente,
    # porque en la sesion tengo almacenada cuanto items hay de cada pelicula,
    # y eso no esta almacenado en film_details. Por ello, busco el id de
    # la pelicula, y hago un remove con el índice donde se encuentra
    id_pelicula = film_details['id']

    for film_carrito in session['peliculas_carrito']:
        if film_carrito['id'] == id_pelicula:
            session['peliculas_carrito'].remove(film_carrito)
            session.modified = True
            return redirect(url_for('carrito'))

    return redirect(url_for('carrito'))


@app.route('/realizar_pago', methods=['GET', 'POST'])
def realizar_pago():
    # Hay que haber iniciado sesion para realizar la compra
    if 'usuario' not in session.keys():
        return redirect(url_for('login'))

    else:
        logged_user = session['usuario']
        usersfolder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'usuarios')
        personalfolder = os.path.join(usersfolder, logged_user, 'data.dat')

        # diccionario con el data.dat
        dict = data_to_dict(personalfolder)
        dinero_actual = dict['Saldo']

        # Calculamos el precio que se está intentando pagar
        lista_peliculas = None
        precio_pedido = 0
        if 'peliculas_carrito' in session.keys():
            lista_peliculas = session['peliculas_carrito']

            for pelicula in lista_peliculas:
                precio_pedido += pelicula['precio'] * pelicula['cantidad']

        # En el carrito de la compra, escribo que no hay suficiente dinero
        if float(dinero_actual) < float(precio_pedido):
            error = {'mensaje': 'Saldo insuficiente. Su saldo actual es {0:.2f}'.format(
                float(dinero_actual)) + "$. Añada saldo para completar la compra"}
            return render_template('carrito.html', title='Carrito', lista_peliculas=lista_peliculas, precio=precio_pedido, aux=error)

        # Reemplazamos el data.dat para actualizar el saldo restante
        # Vaciamos la informacion del carrito de la sesion
        else:
            update_historial_pedidos()
            session.pop('peliculas_carrito', None)
            session.modified = True
            f = open(personalfolder, "w+")
            for key in dict:
                if key == 'Saldo':
                    f.write("{} : {}\n".format(key, str(round(float(dinero_actual) - float(precio_pedido), 2))))
                else:
                    f.write("{} : {}\n".format(key, dict[key]))
            f.close()
            session['saldo'] = str(round(float(dinero_actual) - float(precio_pedido), 2))
            session.modified = True
            compra = {'mensaje': 'Compra efectuada correctamente. Su saldo restante es {0:.2f}'.format(
                float(dinero_actual) - float(precio_pedido)) + "$"}
            return render_template('carrito.html', Title="Carrito", aux=compra)


@app.route('/aniadir_saldo', methods=['GET', 'POST'])
def aniadir_saldo():
    # Hay que haber iniciado sesion para añadir saldo
    if 'usuario' not in session.keys():
        return redirect(url_for('login'))
    else:
        # Si nos llaman con post, leemos los datos y aumentamos el saldo
        if request.method == 'POST':
            usersfolder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'usuarios')
            personalfolder = os.path.join(usersfolder, request.form['Username'], 'data.dat')

            # Comprobamos si el usuario existe REVISAR
            if not os.path.exists(usersfolder) or not os.path.exists(personalfolder):
                err_text = "No existe el usuario " + request.form['Username']
                context_dict = {'text': err_text}
                return render_template('aniadir_saldo.html', title="Añadir Saldo", message=context_dict)

            else:
                # dictionary with the data.dat file
                dict = data_to_dict(personalfolder)
                if dict['Username'] == request.form['Username'] and dict['CVV'] == str(request.form['CVV']):
                    dinero_actual = float(dict['Saldo'])
                    dinero_actual += float(request.form['price'])

                    # Reemplazamos el data.dat para actualizar el saldo restante
                    f = open(personalfolder, "w+")
                    for key in dict:
                        if key == 'Saldo':
                            f.write("{} : {}\n".format(key, str(dinero_actual)))
                        else:
                            f.write("{} : {}\n".format(key, dict[key]))
                    f.close()
                    session['saldo'] = str(round(dinero_actual, 2))
                    session.modified = True

                    return redirect(url_for('index'))

                else:
                    err_text = "Los datos de seguridad no coinciden, intentelo de nuevo mas tarde"
                    context_dict = {'text': err_text}
                    return render_template('aniadir_saldo.html', title="Añadir Saldo", message=context_dict)
        else:
            return render_template('aniadir_saldo.html', title="Añadir Saldo")


@app.route('/people', methods=['GET', 'POST'])
def people():
    if request.method == "GET":
        try:
            return str(random.randint(900, 1000))
        except Exception as e:
            return "error: " + str(e)
