from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
from .models import db, User, Company, Appeal, CreditHistory
from werkzeug.security import generate_password_hash, check_password_hash
from .utils_cedulave import validar_cedula, validar_rif
from .planes import PLANES, Plan
import requests

main = Blueprint('main', __name__)

@main.route('/api/consulta_cedula', methods=['POST'])
def api_consulta_cedula():
    data = request.get_json()
    cedula = data.get('cedula')
    nacionalidad = data.get('nacionalidad', 'V')
    if not cedula or not nacionalidad:
        return jsonify({'success': False, 'error': 'Cédula y nacionalidad requeridas.'})
    # Buscar en base de datos local primero
    cliente = User.query.filter_by(cedula=cedula).first()
    if cliente:
        # Simplificado: puedes mapear los campos según tu modelo
        return jsonify({'success': True, 'cliente': {
            'id': cliente.id,
            'cedula': cliente.cedula,
            'primer_nombre': cliente.nombre.split(' ')[0] if cliente.nombre else '',
            'primer_apellido': cliente.apellido.split(' ')[0] if cliente.apellido else '',
            'rif': getattr(cliente, 'rif', ''),
            'telefono': getattr(cliente, 'telefono', ''),
            'email': getattr(cliente, 'email', ''),
            'direccion': getattr(cliente, 'direccion', ''),
            'score': getattr(cliente, 'score', None),
        }})
    # Consultar API externa
    api_data = validar_cedula(cedula, nacionalidad)
    # La API cedula.com.ve retorna {'error': False, 'error_str': False, 'data': {...}}
    if api_data and (('success' in api_data and api_data.get('success') and api_data.get('data')) or (api_data.get('error') is False and api_data.get('data'))):
        # Buscar si existe el cliente en la base de datos
        db_cliente = User.query.filter_by(cedula=str(api_data['data'].get('cedula'))).first()
        cliente_data = dict(api_data['data'])
        if db_cliente:
            cliente_data['id'] = db_cliente.id
        return jsonify({'success': True, 'cliente': cliente_data})
    elif api_data and api_data.get('error_str') == 'RECORD_NOT_FOUND':
        # Mostrar modal de registro
        return jsonify({'success': False, 'registro': True, 'cedula': cedula, 'nacionalidad': nacionalidad})
    elif api_data and api_data.get('error_str'):
        # Otros errores de la API (límite, token, etc.)
        return jsonify({'success': False, 'error': api_data.get('error_str')})
    else:
        return jsonify({'success': False, 'error': 'No se pudo validar la cédula.'})

@main.route('/api/registrar_persona', methods=['POST'])
def api_registrar_persona():
    nombre = request.form.get('nombre')
    apellido = request.form.get('apellido')
    cedula = request.form.get('cedula')
    nacionalidad = request.form.get('nacionalidad')
    direccion = request.form.get('direccion')
    email = request.form.get('email')
    telefono = request.form.get('telefono')
    # Puedes agregar validaciones adicionales aquí
    if not nombre or not apellido or not cedula or not nacionalidad:
        return jsonify({'success': False, 'error': 'Faltan campos obligatorios.'})
    if User.query.filter_by(cedula=cedula).first():
        return jsonify({'success': False, 'error': 'Ya existe un usuario con esa cédula.'})
    nuevo = User(nombre=nombre, apellido=apellido, cedula=cedula, nacionalidad=nacionalidad, direccion=direccion, email=email, telefono=telefono)
    db.session.add(nuevo)
    db.session.commit()
    return jsonify({'success': True})

@main.route('/')
def home():
    return redirect(url_for('main.login'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        login_type = request.form.get('login_type')
        email = request.form.get('email')
        password = request.form.get('password')
        print(f"[LOGIN][POST] login_type: {login_type}, email: {email}, password: {password}")
        user = None
        tipo = None
        if login_type == 'empresa':
            user = Company.query.filter_by(email=email).first()
            tipo = 'empresa'
            print(f"[LOGIN][EMPRESA] Buscando empresa con email: {email}")
        elif login_type == 'usuario':
            user = User.query.filter_by(email=email).first()
            tipo = 'usuario'
            print(f"[LOGIN][USUARIO] Buscando usuario con email: {email}")
        if user and user.password and check_password_hash(user.password, password):
            print(f"[LOGIN][EXITO] Usuario {email} autenticado correctamente")
            session['user_id'] = user.id
            session['tipo'] = tipo
            flash('Inicio de sesión exitoso', 'success')
            if tipo == 'empresa':
                return redirect(url_for('main.dashboard_empresa'))
            else:
                return redirect(url_for('main.dashboard'))
        else:
            print(f"[LOGIN][ERROR] Credenciales incorrectas o usuario no existe para {email}")
            error = 'Credenciales incorrectas o usuario no existe.'
    return render_template('login.html', error=error)

@main.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        login_type = request.form.get('login_type')
        email = request.form.get('email')
        password = request.form.get('password')
        nombre_usuario = request.form.get('nombre_usuario')
        nombre_empresa = request.form.get('nombre_empresa')
        apellido = request.form.get('apellido')
        cedula = request.form.get('cedula')
        rif = request.form.get('rif')
        plan = request.form.get('plan')
        print(f"[REGISTRO][POST] login_type: {login_type}, email: {email}, password: {password}, nombre_usuario: {nombre_usuario}, nombre_empresa: {nombre_empresa}, apellido: {apellido}, cedula: {cedula}, rif: {rif}, plan: {plan}")
        if login_type == 'empresa':
            nombre = nombre_empresa
            print(f"[REGISTRO][EMPRESA] Datos recibidos: nombre={nombre}, rif={rif}, email={email}, password={password}, plan={plan}")
            # Validar campos requeridos
            if not nombre or not rif or not email or not password or not plan:
                print(f"[REGISTRO][EMPRESA][ERROR] Falta algún campo obligatorio.")
                error = 'Todos los campos son obligatorios para empresa.'
            elif Company.query.filter_by(email=email).first() or Company.query.filter_by(rif=rif).first():
                print(f"[REGISTRO][EMPRESA][ERROR] Email o RIF ya registrado.")
                error = 'Email o RIF ya registrado.'
            else:
                validacion_rif = validar_rif(rif)
                print(f"[REGISTRO][EMPRESA] Resultado validación RIF: {validacion_rif}")
                if validacion_rif is False:
                    print(f"[REGISTRO][EMPRESA][ERROR] RIF no válido según CedulaVE API.")
                    error = 'El RIF ingresado no es válido según el registro nacional.'
                else:
                    if validacion_rif is None:
                        print(f"[REGISTRO][EMPRESA][WARN] No se pudo validar RIF por conexión.")
                        flash('Advertencia: No se pudo validar el RIF por problemas de conexión con el registro nacional. El registro continuará.', 'warning')
                    try:
                        company = Company(
                            name=nombre,
                            rif=rif,
                            email=email,
                            password=generate_password_hash(password),
                            plan=plan
                        )
                        db.session.add(company)
                        db.session.commit()
                        print(f"[REGISTRO][EMPRESA][OK] Empresa registrada: {email}, {rif}")
                        flash('Empresa registrada correctamente, inicia sesión', 'success')
                        return redirect(url_for('main.login'))
                    except Exception as e:
                        print(f"[REGISTRO][EMPRESA][ERROR] Excepción al registrar empresa: {e}")
                        error = 'Error interno al registrar empresa.'
        elif login_type == 'usuario':
            nombre = nombre_usuario
            print(f"[REGISTRO][USUARIO] Datos recibidos: nombre={nombre}, apellido={apellido}, cedula={cedula}, email={email}, password={password}, plan={plan}")
            if not nombre or not apellido or not cedula or not email or not password or not plan:
                print(f"[REGISTRO][USUARIO][ERROR] Falta algún campo obligatorio.")
                error = 'Todos los campos son obligatorios para usuario.'
            elif User.query.filter_by(email=email).first() or User.query.filter_by(cedula=cedula).first():
                print(f"[REGISTRO][USUARIO][ERROR] Email o cédula ya registrado.")
                error = 'Email o cédula ya registrado.'
            else:
                validacion_cedula = validar_cedula(cedula)
                print(f"[REGISTRO][USUARIO] Resultado validación cédula: {validacion_cedula}")
                if validacion_cedula is False:
                    print(f"[REGISTRO][USUARIO][ERROR] Cédula no válida según CedulaVE API.")
                    error = 'La cédula ingresada no es válida según el registro nacional.'
                else:
                    if validacion_cedula is None:
                        print(f"[REGISTRO][USUARIO][WARN] No se pudo validar cédula por conexión.")
                        flash('Advertencia: No se pudo validar la cédula por problemas de conexión con el registro nacional. El registro continuará.', 'warning')
                    try:
                        user = User(
                            nombre=nombre,
                            apellido=apellido,
                            cedula=cedula,
                            email=email,
                            password=generate_password_hash(password),
                            plan=plan
                        )
                        db.session.add(user)
                        db.session.commit()
                        # Vincular reportes previos a este user
                        from .models import Appeal
                        nacionalidad = request.form.get('nacionalidad')
                        appeals = Appeal.query.filter_by(cedula=cedula, nacionalidad=nacionalidad, user_id=None).all()
                        for appeal in appeals:
                            appeal.user_id = user.id
                        db.session.commit()
                        db.session.commit()
                        print(f"[REGISTRO][USUARIO][OK] Usuario registrado: {email}, {cedula}")
                        flash('Usuario registrado correctamente, inicia sesión', 'success')
                        return redirect(url_for('main.login'))
                    except Exception as e:
                        print(f"[REGISTRO][USUARIO][ERROR] Excepción al registrar usuario: {e}")
                        error = 'Error interno al registrar usuario.'
    return render_template('register.html', error=error)

def usuario_puede_consultar_credito(usuario):
    """
    Lógica de control de acceso a consulta de vida crediticia según el plan.
    - Bronce: solo 2 consultas/mes, solo gráfica básica.
    - Plata/Oro/Diamante: acceso completo.
    """
    if usuario.plan == Plan.BRONCE:
        # Suponiendo que usuario tiene un campo consultas_realizadas_mes
        if getattr(usuario, 'consultas_realizadas_mes', 0) >= 2:
            return False, 'Has alcanzado el límite de 2 consultas este mes. Mejora tu plan para más beneficios.'
        return True, 'Consulta básica disponible.'
    else:
        return True, 'Consulta premium disponible.'

@main.route('/empresa/reportar_cliente', methods=['GET', 'POST'])
@main.route('/empresa/reportar_cliente/<int:cliente_id>', methods=['GET', 'POST'])
def reportar_cliente(cliente_id=None):
    from .models import User, Appeal
    from app import db
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'empresa' or not user_id:
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('main.dashboard'))
    # Permitir acceso por id o por query params
    cliente = None
    cedula = request.args.get('cedula')
    nacionalidad = request.args.get('nacionalidad', 'V')
    if cliente_id:
        cliente = User.query.get_or_404(cliente_id)
    elif cedula:
        cliente = User.query.filter_by(cedula=cedula).first()
    if request.method == 'POST':
        motivo = request.form.get('motivo')
        comentario = request.form.get('comentario')
        archivo = request.files.get('pruebas')
        pruebas_path = None
        if archivo:
            pruebas_path = f'uploads/{archivo.filename}'
            archivo.save(pruebas_path)
        # Si existe cliente, asociar a user_id; si no, guardar cedula/nacionalidad
        user_id_cliente = cliente.id if cliente else None
        apelacion = Appeal(
            motivo=motivo,
            comentario=comentario,
            pruebas=pruebas_path,
            estado='pendiente',
            fecha_creacion=datetime.utcnow(),
            user_id=user_id_cliente,
            credit_history_id=None
        )
        # Guardar cedula/nacionalidad si no hay user_id
        if not user_id_cliente:
            apelacion.cedula = cedula
            apelacion.nacionalidad = nacionalidad
        db.session.add(apelacion)
        db.session.commit()
        flash('Cliente reportado correctamente. Se ha generado una apelación para revisión.', 'success')
        return redirect(url_for('main.dashboard_empresa'))
    return render_template('reportar_cliente.html', cliente=cliente, cedula=cedula, nacionalidad=nacionalidad)


@main.route('/empresa/modificar_score', methods=['GET','POST'])
@main.route('/empresa/modificar_score/<int:cliente_id>', methods=['GET','POST'])
def modificar_score(cliente_id=None):
    from .models import User
    from app import db
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'empresa' or not user_id:
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('main.dashboard'))
    cedula = request.args.get('cedula')
    nacionalidad = request.args.get('nacionalidad')
    cliente = None
    if cliente_id:
        cliente = User.query.get(cliente_id)
    elif cedula and nacionalidad:
        cliente = User.query.filter_by(cedula=cedula, nacionalidad=nacionalidad).first()
    # Si no hay cliente, el formulario permitirá modificar por cedula/nacionalidad
    if request.method == 'POST':
        try:
            evento = request.form.get('evento')
            comentario = request.form.get('comentario')
            impacto_map = {
                'pago_puntual': 10,
                'mora_leve': -25,
                'mora_grave': -60,
                'cuenta_cerrada': 5,
                'incumplimiento': -100,
                'nuevo_credito': -10,
            }
            evento_nombre = {
                'pago_puntual': 'Pago puntual',
                'mora_leve': 'Mora leve (<30 días)',
                'mora_grave': 'Mora grave (>90 días)',
                'cuenta_cerrada': 'Cuenta cerrada',
                'incumplimiento': 'Incumplimiento total',
                'nuevo_credito': 'Nuevo crédito',
            }
            impacto = impacto_map.get(evento, 0)
            if cliente:
                score_nuevo = cliente.score + impacto
            else:
                score_nuevo = None
            nuevo_evento = CreditHistory(
                tipo=evento,
                estado='cerrado',
                monto=0,
                fecha_apertura=datetime.utcnow(),
                fecha_cierre=datetime.utcnow(),
                score_impact=impacto,
                comentario=comentario,
                motivo=evento_nombre.get(evento, evento),
                pruebas=None,
                user_id=cliente.id if cliente else None,
                company_id=user_id
            )
            if cliente:
                cliente.score = score_nuevo
                db.session.add(nuevo_evento)
                db.session.commit()
                flash(f'Score actualizado correctamente. Impacto: {impacto:+d} puntos.', 'success')
                return redirect(url_for('main.dashboard_empresa'))
            else:
                db.session.add(nuevo_evento)
                db.session.commit()
                flash(f'Evento registrado para cédula {cedula} y nacionalidad {nacionalidad}.', 'success')
                return render_template('modificar_score.html', cliente=cliente, cedula=cedula, nacionalidad=nacionalidad)
        except Exception as e:
            flash('Error al actualizar el score: ' + str(e), 'danger')
            return render_template('modificar_score.html', cliente=cliente, cedula=cedula, nacionalidad=nacionalidad)
    return render_template('modificar_score.html', cliente=cliente, cedula=cedula, nacionalidad=nacionalidad)

@main.route('/empresa/crear_cliente', methods=['POST'])
def crear_cliente_empresa():
    from .models import User
    from app import db
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'empresa' or not user_id:
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('main.dashboard'))
    cedula = request.form.get('cedula')
    nombre = request.form.get('nombre')
    apellido = request.form.get('apellido')
    direccion = request.form.get('direccion')
    email = request.form.get('email')
    telefono = request.form.get('telefono')
    password = request.form.get('password')
    from werkzeug.security import generate_password_hash
    if not (cedula and nombre and apellido and email and password):
        flash('Todos los campos obligatorios deben ser completados.', 'warning')
        return redirect(url_for('main.dashboard_empresa'))
    if User.query.filter_by(cedula=cedula).first():
        flash('Ya existe un usuario con esa cédula.', 'warning')
        return redirect(url_for('main.dashboard_empresa'))
    if User.query.filter_by(email=email).first():
        flash('Ya existe un usuario con ese correo.', 'warning')
        return redirect(url_for('main.dashboard_empresa'))
    nuevo = User(
        cedula=cedula,
        nombre=nombre,
        apellido=apellido,
        direccion=direccion,
        telefono=telefono,
        email=email,
        password=generate_password_hash(password),
        score=950
    )
    db.session.add(nuevo)
    db.session.commit()
    flash('Cliente creado exitosamente con score máximo.', 'success')
    return redirect(url_for('main.dashboard_empresa'))

@main.route('/dashboard_empresa', methods=['GET', 'POST'])
def dashboard_empresa():
    company = None
    cliente = None
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    credit_history_list = []
    score_color = None
    clientes_registrados = 0
    if tipo == 'empresa' and user_id:
        from .models import Company, User, CreditHistory
        company = Company.query.get(user_id)
        # Ejemplo: contar todos los usuarios (ajusta esto si hay relación directa con la empresa)
        clientes_registrados = User.query.count()
        if request.method == 'POST':
            identificador = request.form.get('identificador')
            # Buscar cliente por cédula o RIF
            cliente = User.query.filter_by(cedula=identificador).first()
            if not cliente:
                # Mostrar opción para crear usuario
                return render_template('dashboard_empresa.html', company=company, cliente=None, crear_nuevo=True, cedula_nueva=identificador, credit_history_list=[], score_color=None, clientes_registrados=clientes_registrados)
        # Si hay cliente, obtener historial y color de score
        if cliente:
            credit_history_list = CreditHistory.query.filter_by(user_id=cliente.id).order_by(CreditHistory.fecha_apertura.desc()).all()
            s = cliente.score
            if s <= 400:
                score_color = 'bg-red-500 text-white'
            elif s == 450:
                score_color = 'bg-yellow-400 text-gray-900'
            elif 550 <= s < 650:
                score_color = 'bg-orange-400 text-white'
            elif 650 <= s < 750:
                score_color = 'bg-blue-500 text-white'
            elif s >= 750:
                score_color = 'bg-green-500 text-white'
    return render_template('dashboard_empresa.html', company=company, cliente=cliente, credit_history_list=credit_history_list, score_color=score_color, clientes_registrados=clientes_registrados)

@main.route('/dashboard')
def dashboard():
    user = None
    company = None
    pending_apelaciones_count = 0
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    credit_history_list = []
    consultas_mes = 0
    if tipo == 'usuario' and user_id:
        user = User.query.get(user_id)
        from .models import Appeal, CreditHistory, ConsultaCredito
        pending_apelaciones_count = Appeal.query.filter_by(user_id=user_id, estado='pendiente').count()
        credit_history_list = CreditHistory.query.filter_by(user_id=user_id).order_by(CreditHistory.fecha_apertura.desc()).all()
        # Contar consultas del mes
        from datetime import datetime
        primer_dia_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        consultas_mes = ConsultaCredito.query.filter(
            ConsultaCredito.user_id == user_id,
            ConsultaCredito.fecha >= primer_dia_mes
        ).count()
    elif tipo == 'empresa' and user_id:
        company = Company.query.get(user_id)
    return render_template('dashboard.html', user=user, company=company, pending_apelaciones_count=pending_apelaciones_count, credit_history_list=credit_history_list, consultas_mes=consultas_mes)

@main.route('/consultar_credito', methods=['POST'])
def consultar_credito():
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'usuario' or not user_id:
        flash('Debes iniciar sesión como usuario para consultar tu vida crediticia.', 'error')
        return redirect(url_for('main.login'))
    user = User.query.get(user_id)
    permitido, mensaje = usuario_puede_consultar_credito(user)
    if not permitido:
        flash(mensaje, 'warning')
        return redirect(url_for('main.dashboard'))
    # Simula datos de vida crediticia
    # Incrementa las consultas realizadas
    from .models import ConsultaCredito
    nueva_consulta = ConsultaCredito(user_id=user.id)
    db.session.add(nueva_consulta)
    db.session.commit()
    from .models import CreditHistory
    credit_history = CreditHistory.query.filter_by(user_id=user.id).order_by(CreditHistory.fecha_apertura.desc()).all()
    historial = []
    reportes_mora = 0
    for h in credit_history:
        historial.append({
            'fecha': h.fecha_apertura.strftime('%Y-%m-%d') if h.fecha_apertura else '-',
            'evento': h.tipo,
            'comentario': h.comentario,
            'impacto': h.score_impact,
            'monto': h.monto if hasattr(h, 'monto') else ''
        })
        if 'mora' in (h.tipo or '').lower():
            reportes_mora += 1
    reporte = {
        'score': user.score,
        'cuentas_abiertas': 2,  # Puedes calcularlo si tienes esa lógica
        'cuentas_cerradas': 1,  # Puedes calcularlo si tienes esa lógica
        'reportes_mora': reportes_mora,
        'historial': historial
    }
    return render_template('reporte_credito.html', user=user, reporte=reporte)

@main.route('/reportes_usuario')
def reportes_usuario():
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'usuario' or not user_id:
        flash('Debes iniciar sesión como usuario para ver los reportes.', 'error')
        return redirect(url_for('main.login'))
    user = User.query.get(user_id)
    from .models import CreditHistory, ConsultaCredito
    # Score evolution (últimos 6 eventos)
    credit_history = CreditHistory.query.filter_by(user_id=user_id).order_by(CreditHistory.fecha_apertura.asc()).all()
    score_labels = [h.fecha_apertura.strftime('%b %Y') if h.fecha_apertura else '-' for h in credit_history[-6:]]
    score_data = [h.score_impact for h in credit_history[-6:]] if credit_history else []
    # Consultas por mes (últimos 6 meses)
    from datetime import datetime, timedelta
    now = datetime.now()
    consultas_labels = []
    consultas_data = []
    for i in range(5, -1, -1):
        mes = (now.replace(day=1) - timedelta(days=30*i)).replace(day=1)
        siguiente_mes = (mes + timedelta(days=32)).replace(day=1)
        label = mes.strftime('%b %Y')
        count = ConsultaCredito.query.filter(
            ConsultaCredito.user_id == user_id,
            ConsultaCredito.fecha >= mes,
            ConsultaCredito.fecha < siguiente_mes
        ).count()
        consultas_labels.append(label)
        consultas_data.append(count)
    return render_template('reportes_usuario.html', user=user, credit_history=credit_history, score_labels=score_labels, score_data=score_data, consultas_labels=consultas_labels, consultas_data=consultas_data)

@main.route('/perfil')
def perfil():
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'usuario' or not user_id:
        flash('Debes iniciar sesión como usuario para ver tu perfil.', 'error')
        return redirect(url_for('main.login'))
    user = User.query.get(user_id)
    return render_template('perfil.html', user=user)

@main.route('/cambiar_plan', methods=['POST'])
def cambiar_plan():
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'usuario' or not user_id:
        flash('Debes iniciar sesión como usuario para cambiar tu plan.', 'error')
        return redirect(url_for('main.login'))
    user = User.query.get(user_id)
    nuevo_plan = request.form.get('nuevo_plan')
    if not nuevo_plan or nuevo_plan == user.plan:
        flash('Debes seleccionar un plan diferente al actual.', 'warning')
        return redirect(url_for('main.dashboard'))
    user.plan = nuevo_plan
    user.consultas_realizadas_mes = 0  # Reinicia el contador de consultas
    db.session.commit()
    flash(f'Tu plan ha sido actualizado a {nuevo_plan.capitalize()} exitosamente.', 'success')
    return redirect(url_for('main.dashboard'))

import os
from werkzeug.utils import secure_filename

# --- RUTA PARA ENVIAR UNA APELACIÓN ---
@main.route('/apelar_reporte', methods=['POST'])
def apelar_reporte():
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'usuario' or not user_id:
        flash('Debes iniciar sesión como usuario para apelar.', 'error')
        return redirect(url_for('main.login'))
    user = User.query.get(user_id)
    if user.plan == 'bronce':
        flash('El plan Bronce no permite apelar reportes.', 'warning')
        return redirect(url_for('main.dashboard'))
    motivo = request.form.get('motivo')
    comentario = request.form.get('comentario')
    credit_history_id = request.form.get('credit_history_id')
    archivo = request.files.get('evidencia')
    ruta_archivo = None
    if archivo and archivo.filename:
        filename = secure_filename(archivo.filename)
        upload_folder = os.path.join(os.getcwd(), 'app', 'static', 'evidencias')
        os.makedirs(upload_folder, exist_ok=True)
        ruta_archivo = os.path.join('static', 'evidencias', filename)
        archivo.save(os.path.join(upload_folder, filename))
    apelacion = Appeal(
        motivo=motivo,
        comentario=comentario,
        pruebas=ruta_archivo,
        user_id=user_id,
        credit_history_id=credit_history_id
    )
    db.session.add(apelacion)
    db.session.commit()
    flash('Tu apelación ha sido enviada y será revisada por un administrador.', 'success')
    return redirect(url_for('main.dashboard'))

# --- RUTA PARA VER LAS APELACIONES DEL USUARIO ---
@main.route('/mis_apelaciones')
def mis_apelaciones():
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'usuario' or not user_id:
        flash('Debes iniciar sesión como usuario.', 'error')
        return redirect(url_for('main.login'))
    apelaciones = Appeal.query.filter_by(user_id=user_id).order_by(Appeal.fecha_creacion.desc()).all()
    return render_template('mis_apelaciones.html', apelaciones=apelaciones)

# --- RUTA PARA QUE EL ADMIN GESTIONE APELACIONES ---
@main.route('/admin/apelaciones', methods=['GET', 'POST'])
def admin_apelaciones():
    # Aquí deberías agregar lógica de autenticación de admin
    if request.method == 'POST':
        apelacion_id = request.form.get('apelacion_id')
        accion = request.form.get('accion')  # 'aprobar' o 'rechazar'
        apelacion = Appeal.query.get(apelacion_id)
        if apelacion:
            if accion == 'aprobar':
                apelacion.estado = 'aprobada'
            elif accion == 'rechazar':
                apelacion.estado = 'rechazada'
            db.session.commit()
            flash('Estado de apelación actualizado.', 'success')
    apelaciones = Appeal.query.order_by(Appeal.fecha_creacion.desc()).all()
    return render_template('admin_apelaciones.html', apelaciones=apelaciones)

@main.route('/logout')
def logout():
    session.clear()
    flash('Sesión finalizada', 'info')
    return redirect(url_for('main.login'))
