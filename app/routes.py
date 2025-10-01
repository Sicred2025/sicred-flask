from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from datetime import datetime, timedelta
from .models import db, User, Company, Appeal, CreditHistory, Notification, ScoreChange, Alert, CreditReport, PaymentHistory, UserSession, AuditLog
from werkzeug.security import generate_password_hash, check_password_hash
from .utils_cedulave import validar_cedula, validar_rif
from .planes import PLANES, Plan
import requests
import json
import uuid
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

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
    enriquecido = False
    if cliente:
        # Si faltan datos clave, consultar API externa y actualizar
        datos_faltantes = not cliente.nombre or not cliente.apellido or not cliente.direccion or not cliente.telefono or not cliente.email
        if datos_faltantes:
            api_data = validar_cedula(cedula, nacionalidad)
            if api_data and api_data.get('data'):
                data_api = api_data['data']
                # Actualizar solo si hay datos nuevos
                if not cliente.nombre and data_api.get('primer_nombre'):
                    cliente.nombre = data_api.get('primer_nombre')
                    enriquecido = True
                if not cliente.apellido and data_api.get('primer_apellido'):
                    cliente.apellido = data_api.get('primer_apellido')
                    enriquecido = True
                if not cliente.direccion and data_api.get('direccion'):
                    cliente.direccion = data_api.get('direccion')
                    enriquecido = True
                if not cliente.telefono and data_api.get('telefono'):
                    cliente.telefono = data_api.get('telefono')
                    enriquecido = True
                if not cliente.email and data_api.get('email'):
                    cliente.email = data_api.get('email')
                    enriquecido = True
                db.session.commit()
        # Preparar ficha profesional completa
        ficha = {
            'id': cliente.id,
            'cedula': cliente.cedula,
            'nacionalidad': cliente.nacionalidad,
            'nombre': cliente.nombre,
            'apellido': cliente.apellido,
            'telefono': cliente.telefono,
            'email': cliente.email,
            'direccion': cliente.direccion,
            'score': cliente.score,
            'enriquecido': enriquecido,
        }
        # Buscar historial
        from .models import CreditHistory
        historial = CreditHistory.query.filter_by(user_id=cliente.id).order_by(CreditHistory.fecha_apertura.desc()).all()
        ficha['historial'] = [
            {
                'fecha': h.fecha_apertura.strftime('%Y-%m-%d') if h.fecha_apertura else '-',
                'evento': h.tipo,
                'comentario': h.comentario,
                'impacto': h.score_impact,
                'monto': h.monto if hasattr(h, 'monto') else ''
            } for h in historial
        ]
        return jsonify({'success': True, 'cliente': ficha})
    # Consultar API externa si no existe
    api_data = validar_cedula(cedula, nacionalidad)
    if api_data and (('success' in api_data and api_data.get('success') and api_data.get('data')) or (api_data.get('error') is False and api_data.get('data'))):
        db_cliente = User.query.filter_by(cedula=str(api_data['data'].get('cedula'))).first()
        cliente_data = dict(api_data['data'])
        if db_cliente:
            cliente_data['id'] = db_cliente.id
        return jsonify({'success': True, 'cliente': cliente_data})
    elif api_data and api_data.get('error_str') == 'RECORD_NOT_FOUND':
        return jsonify({'success': False, 'registro': True, 'cedula': cedula, 'nacionalidad': nacionalidad})
    elif api_data and api_data.get('error_str'):
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
    cliente = None
    cedula = request.args.get('cedula')
    nacionalidad = request.args.get('nacionalidad', 'V')
    if cliente_id:
        cliente = User.query.get_or_404(cliente_id)
    elif cedula:
        cliente = User.query.filter_by(cedula=cedula).first()
    if request.method == 'POST':
        # Capturar todos los datos del formulario
        cedula_form = request.form.get('cedula')
        nacionalidad_form = request.form.get('nacionalidad')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        direccion = request.form.get('direccion')
        motivo = request.form.get('motivo')
        comentario = request.form.get('comentario')
        archivo = request.files.get('pruebas')
        pruebas_path = None
        if archivo and archivo.filename:
            pruebas_path = f'uploads/{archivo.filename}'
            archivo.save(pruebas_path)
        # Buscar o crear cliente
        if cliente_id:
            cliente = User.query.get(cliente_id)
        elif cedula_form and nacionalidad_form:
            cliente = User.query.filter_by(cedula=cedula_form, nacionalidad=nacionalidad_form).first()
        if not cliente:
            random_password = generate_password_hash(str(uuid.uuid4()))
            cliente = User(
                cedula=cedula_form,
                nacionalidad=nacionalidad_form,
                nombre=nombre,
                apellido=apellido,
                email=email,
                telefono=telefono,
                direccion=direccion,
                password=random_password,
                is_verified=False,
                score=450
            )
            db.session.add(cliente)
            db.session.commit()
        else:
            cliente.nombre = nombre
            cliente.apellido = apellido
            cliente.email = email
            cliente.telefono = telefono
            cliente.direccion = direccion
            db.session.commit()
        # Crear el reporte (Appeal)
        apelacion = Appeal(
            motivo=motivo,
            comentario=comentario,
            pruebas=pruebas_path,
            estado='pendiente',
            fecha_creacion=datetime.utcnow(),
            user_id=cliente.id,
            credit_history_id=None,
            cedula=cedula_form,
            nacionalidad=nacionalidad_form
        )
        db.session.add(apelacion)
        db.session.commit()
        # Registrar evento en CreditHistory para que aparezca en reportes
        from .models import CreditHistory
        nuevo_evento = CreditHistory(
            tipo='reporte_empresa',
            estado='pendiente',
            monto=0,
            fecha_apertura=datetime.utcnow(),
            fecha_cierre=None,
            score_impact=0,
            comentario=comentario,
            motivo=motivo,
            pruebas=pruebas_path,
            user_id=cliente.id,
            company_id=user_id
        )
        db.session.add(nuevo_evento)
        db.session.commit()
        flash('Cliente reportado correctamente. Se ha generado una apelación para revisión.', 'success')
        return redirect(url_for('main.dashboard_empresa'))
    return render_template('reportar_cliente.html', cliente=cliente, cedula=cedula, nacionalidad=nacionalidad)


@main.route('/empresa/modificar_score', methods=['GET','POST'])
@main.route('/empresa/modificar_score/<int:cliente_id>', methods=['GET','POST'])
def modificar_score(cliente_id=None):
    from .models import User, CreditHistory
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
    if request.method == 'POST':
        try:
            # Capturar todos los datos del formulario
            cedula_form = request.form.get('cedula')
            nacionalidad_form = request.form.get('nacionalidad')
            nombre = request.form.get('nombre')
            apellido = request.form.get('apellido')
            email = request.form.get('email')
            telefono = request.form.get('telefono')
            direccion = request.form.get('direccion')
            evento = request.form.get('evento')
            comentario = request.form.get('comentario')
            impacto = request.form.get('impacto', type=int)
            monto = request.form.get('monto', type=float) or 0
            evento_nombre = {
                'pago_puntual': 'Pago puntual',
                'mora_leve': 'Mora leve (<30 días)',
                'mora_grave': 'Mora grave (>90 días)',
                'cuenta_cerrada': 'Cuenta cerrada',
                'incumplimiento': 'Incumplimiento total',
                'nuevo_credito': 'Nuevo crédito',
            }
            # Buscar o crear cliente
            cliente = None
            if cliente_id:
                cliente = User.query.get(cliente_id)
            elif cedula_form and nacionalidad_form:
                cliente = User.query.filter_by(cedula=cedula_form, nacionalidad=nacionalidad_form).first()
            if not cliente:
                # Crear cliente con todos los datos
                cliente = User(
                    cedula=cedula_form,
                    nacionalidad=nacionalidad_form,
                    nombre=nombre,
                    apellido=apellido,
                    email=email,
                    telefono=telefono,
                    direccion=direccion,
                    score=450+impacto # Score inicial con impacto
                )
                db.session.add(cliente)
                db.session.commit()
            else:
                # Actualizar datos si hay cambios
                cliente.nombre = nombre
                cliente.apellido = apellido
                cliente.email = email
                cliente.telefono = telefono
                cliente.direccion = direccion
                # Actualizar score
                cliente.score = (cliente.score or 450) + impacto
                db.session.commit()
            # Registrar evento de score
            nuevo_evento = CreditHistory(
                tipo=evento,
                estado='cerrado',
                monto=monto,
                fecha_apertura=datetime.utcnow(),
                fecha_cierre=datetime.utcnow(),
                score_impact=impacto,
                comentario=comentario,
                motivo=evento_nombre.get(evento, evento),
                pruebas=None,
                user_id=cliente.id,
                company_id=user_id
            )
            db.session.add(nuevo_evento)
            db.session.commit()
            flash(f'Score actualizado correctamente para {cliente.nombre} {cliente.apellido}. Impacto: {impacto:+d} puntos.', 'success')
            return redirect(url_for('main.dashboard_empresa'))
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
    reportes = []
    filtros = {
        'cliente': request.args.get('filtro_cliente', '').strip(),
        'estado': request.args.get('filtro_estado', ''),
        'fecha_desde': request.args.get('filtro_fecha_desde', ''),
        'fecha_hasta': request.args.get('filtro_fecha_hasta', ''),
    }
    if tipo == 'empresa' and user_id:
        from .models import Company, User, CreditHistory
        company = Company.query.get(user_id)
        clientes_registrados = User.query.count()
        # Filtros para reportes
        query = CreditHistory.query.filter_by(company_id=user_id)
        # Filtro por cliente (nombre o cédula)
        if filtros['cliente']:
            query = query.join(User, CreditHistory.user_id == User.id).filter(
                (User.cedula.ilike(f"%{filtros['cliente']}%")) |
                (User.nombre.ilike(f"%{filtros['cliente']}%")) |
                (User.apellido.ilike(f"%{filtros['cliente']}%"))
            )
        # Filtro por estado
        if filtros['estado']:
            query = query.filter(CreditHistory.estado == filtros['estado'])
        # Filtro por fecha
        if filtros['fecha_desde']:
            try:
                fecha_desde = datetime.strptime(filtros['fecha_desde'], '%Y-%m-%d')
                query = query.filter(CreditHistory.fecha_apertura >= fecha_desde)
            except Exception:
                pass
        if filtros['fecha_hasta']:
            try:
                fecha_hasta = datetime.strptime(filtros['fecha_hasta'], '%Y-%m-%d')
                fecha_hasta = fecha_hasta.replace(hour=23, minute=59, second=59)
                query = query.filter(CreditHistory.fecha_apertura <= fecha_hasta)
            except Exception:
                pass
        reportes = query.order_by(CreditHistory.fecha_apertura.desc()).all()
        # Lógica previa para consulta de cliente
        if request.method == 'POST':
            identificador = request.form.get('identificador')
            cliente = User.query.filter_by(cedula=identificador).first()
            if not cliente:
                return render_template('dashboard_empresa.html', company=company, cliente=None, crear_nuevo=True, cedula_nueva=identificador, credit_history_list=[], score_color=None, clientes_registrados=clientes_registrados, reportes=reportes, filtros=filtros)
        if not cliente and request.method == 'GET':
            identificador = request.args.get('identificador')
            if identificador:
                cliente = User.query.filter_by(cedula=identificador).first()
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
    return render_template('dashboard_empresa.html', company=company, cliente=cliente, credit_history_list=credit_history_list, score_color=score_color, clientes_registrados=clientes_registrados, reportes=reportes, filtros=filtros)

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

# NUEVAS RUTAS PARA FUNCIONALIDADES AVANZADAS

@main.route('/historial_credito')
def historial_credito():
    """Vista detallada del historial crediticio del usuario"""
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'usuario' or not user_id:
        flash('Debes iniciar sesión como usuario para ver tu historial.', 'error')
        return redirect(url_for('main.login'))
    
    user = User.query.get(user_id)
    credit_history = CreditHistory.query.filter_by(user_id=user_id).order_by(CreditHistory.fecha_apertura.desc()).all()
    
    # Estadísticas del historial
    total_cuentas = len(credit_history)
    cuentas_abiertas = len([h for h in credit_history if h.fecha_cierre is None])
    cuentas_cerradas = total_cuentas - cuentas_abiertas
    cuentas_mora = len([h for h in credit_history if 'mora' in (h.estado or '').lower()])
    total_deuda = sum([h.saldo_actual or 0 for h in credit_history if h.saldo_actual])
    
    return render_template('historial_credito.html', 
                         user=user, 
                         credit_history=credit_history,
                         total_cuentas=total_cuentas,
                         cuentas_abiertas=cuentas_abiertas,
                         cuentas_cerradas=cuentas_cerradas,
                         cuentas_mora=cuentas_mora,
                         total_deuda=total_deuda)

@main.route('/analisis_score')
def analisis_score():
    """Análisis detallado del score crediticio"""
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'usuario' or not user_id:
        flash('Debes iniciar sesión como usuario para ver el análisis.', 'error')
        return redirect(url_for('main.login'))
    
    user = User.query.get(user_id)
    score_changes = ScoreChange.query.filter_by(user_id=user_id).order_by(ScoreChange.fecha_cambio.desc()).limit(12).all()
    
    # Datos para gráficos
    fechas = [change.fecha_cambio.strftime('%b %Y') for change in reversed(score_changes)]
    scores = [change.score_nuevo for change in reversed(score_changes)]
    
    # Análisis de tendencia
    if len(score_changes) >= 2:
        tendencia = "Subiendo" if score_changes[0].cambio > 0 else "Bajando" if score_changes[0].cambio < 0 else "Estable"
    else:
        tendencia = "Sin datos suficientes"
    
    return render_template('analisis_score.html', 
                         user=user, 
                         score_changes=score_changes,
                         fechas=fechas,
                         scores=scores,
                         tendencia=tendencia)

@main.route('/notificaciones')
def notificaciones():
    """Vista de notificaciones del usuario"""
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if not user_id:
        flash('Debes iniciar sesión para ver las notificaciones.', 'error')
        return redirect(url_for('main.login'))
    
    if tipo == 'usuario':
        notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.fecha_creacion.desc()).all()
    else:
        notifications = Notification.query.filter_by(company_id=user_id).order_by(Notification.fecha_creacion.desc()).all()
    
    return render_template('notificaciones.html', notifications=notifications)

@main.route('/marcar_notificacion_leida/<int:notification_id>', methods=['POST'])
def marcar_notificacion_leida(notification_id):
    """Marcar una notificación como leída"""
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'No autorizado'})
    
    notification = Notification.query.get(notification_id)
    if notification and ((tipo == 'usuario' and notification.user_id == user_id) or 
                        (tipo == 'empresa' and notification.company_id == user_id)):
        notification.leida = True
        notification.fecha_lectura = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Notificación no encontrada'})

@main.route('/alertas')
def alertas():
    """Vista de alertas del usuario"""
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'usuario' or not user_id:
        flash('Debes iniciar sesión como usuario para ver las alertas.', 'error')
        return redirect(url_for('main.login'))
    
    alertas = Alert.query.filter_by(user_id=user_id, activa=True).order_by(Alert.fecha_creacion.desc()).all()
    return render_template('alertas.html', alertas=alertas)

@main.route('/planes')
def planes():
    """Vista de planes disponibles"""
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    
    if tipo == 'usuario':
        user = User.query.get(user_id) if user_id else None
        return render_template('planes_usuario.html', planes=PLANES, user=user)
    elif tipo == 'empresa':
        company = Company.query.get(user_id) if user_id else None
        return render_template('planes_empresa.html', planes=PLANES, company=company)
    else:
        return render_template('planes_publico.html', planes=PLANES)

@main.route('/configuracion')
def configuracion():
    """Vista de configuración del usuario"""
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if not user_id:
        flash('Debes iniciar sesión para acceder a la configuración.', 'error')
        return redirect(url_for('main.login'))
    
    if tipo == 'usuario':
        user = User.query.get(user_id)
        return render_template('configuracion_usuario.html', user=user)
    else:
        company = Company.query.get(user_id)
        return render_template('configuracion_empresa.html', company=company)

@main.route('/cambiar_password', methods=['GET', 'POST'])
def cambiar_password():
    """Cambiar contraseña del usuario"""
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if not user_id:
        flash('Debes iniciar sesión para cambiar tu contraseña.', 'error')
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        password_actual = request.form.get('password_actual')
        password_nueva = request.form.get('password_nueva')
        password_confirmar = request.form.get('password_confirmar')
        
        if tipo == 'usuario':
            user = User.query.get(user_id)
        else:
            user = Company.query.get(user_id)
        
        if not user or not check_password_hash(user.password, password_actual):
            flash('La contraseña actual es incorrecta.', 'error')
        elif password_nueva != password_confirmar:
            flash('Las contraseñas nuevas no coinciden.', 'error')
        elif len(password_nueva) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
        else:
            user.password = generate_password_hash(password_nueva)
            db.session.commit()
            
            # Crear log de auditoría
            audit_log = AuditLog(
                user_id=user_id if tipo == 'usuario' else None,
                company_id=user_id if tipo == 'empresa' else None,
                accion='cambiar_password',
                tabla_afectada='users' if tipo == 'usuario' else 'company',
                registro_id=user_id,
                ip_address=request.remote_addr,
                descripcion='Cambio de contraseña exitoso'
            )
            db.session.add(audit_log)
            db.session.commit()
            
            flash('Contraseña cambiada exitosamente.', 'success')
            return redirect(url_for('main.dashboard'))
    
    return render_template('cambiar_password.html')

@main.route('/nueva_apelacion', methods=['GET', 'POST'])
def nueva_apelacion():
    """Crear una nueva apelación"""
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'usuario' or not user_id:
        flash('Debes iniciar sesión como usuario para crear apelaciones.', 'error')
        return redirect(url_for('main.login'))
    
    user = User.query.get(user_id)
    if user.plan == 'bronce':
        flash('El plan Bronce no permite apelar reportes.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        motivo = request.form.get('motivo')
        comentario = request.form.get('comentario')
        credit_history_id = request.form.get('credit_history_id')
        prioridad = request.form.get('prioridad', 'normal')
        
        if not motivo or not credit_history_id:
            flash('Todos los campos son obligatorios.', 'error')
        else:
            apelacion = Appeal(
                motivo=motivo,
                comentario=comentario,
                user_id=user_id,
                credit_history_id=credit_history_id,
                prioridad=prioridad
            )
            db.session.add(apelacion)
            db.session.commit()
            
            flash('Tu apelación ha sido enviada y será revisada por un administrador.', 'success')
            return redirect(url_for('main.mis_apelaciones'))
    
    # Obtener historial crediticio para seleccionar
    credit_history = CreditHistory.query.filter_by(user_id=user_id).order_by(CreditHistory.fecha_apertura.desc()).all()
    return render_template('nueva_apelacion.html', user=user, credit_history=credit_history)

@main.route('/ayuda')
def ayuda():
    """Página de ayuda"""
    return render_template('ayuda.html')

@main.route('/contacto', methods=['GET', 'POST'])
def contacto():
    """Página de contacto"""
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        asunto = request.form.get('asunto')
        mensaje = request.form.get('mensaje')
        
        # Aquí podrías enviar un email o guardar en base de datos
        flash('Tu mensaje ha sido enviado. Te responderemos pronto.', 'success')
        return redirect(url_for('main.contacto'))
    
    return render_template('contacto.html')

@main.route('/faq')
def faq():
    """Página de preguntas frecuentes"""
    return render_template('faq.html')

@main.route('/empresa/ayuda')
def empresa_ayuda():
    return render_template('ayuda.html')

@main.route('/empresa/contacto')
def empresa_contacto():
    return render_template('contacto.html')

@main.route('/empresa/faq')
def empresa_faq():
    return render_template('faq.html')

# API ENDPOINTS PARA FUNCIONALIDADES DINÁMICAS

@main.route('/api/notificaciones_no_leidas')
def api_notificaciones_no_leidas():
    """API para obtener notificaciones no leídas"""
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'count': 0})
    
    if tipo == 'usuario':
        count = Notification.query.filter_by(user_id=user_id, leida=False).count()
    else:
        count = Notification.query.filter_by(company_id=user_id, leida=False).count()
    
    return jsonify({'count': count})

@main.route('/api/alertas_activas')
def api_alertas_activas():
    """API para obtener alertas activas"""
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'usuario' or not user_id:
        return jsonify({'count': 0})
    
    count = Alert.query.filter_by(user_id=user_id, activa=True).count()
    return jsonify({'count': count})

@main.route('/api/score_evolution')
def api_score_evolution():
    """API para obtener evolución del score"""
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'usuario' or not user_id:
        return jsonify({'error': 'No autorizado'})
    
    score_changes = ScoreChange.query.filter_by(user_id=user_id).order_by(ScoreChange.fecha_cambio.asc()).limit(12).all()
    
    data = {
        'fechas': [change.fecha_cambio.strftime('%Y-%m-%d') for change in score_changes],
        'scores': [change.score_nuevo for change in score_changes],
        'cambios': [change.cambio for change in score_changes]
    }
    
    return jsonify(data)

@main.route('/api/reporte_detalle/<int:reporte_id>', methods=['GET'])
def api_reporte_detalle(reporte_id):
    from .models import CreditHistory, User, AuditLog
    rep = CreditHistory.query.get_or_404(reporte_id)
    cliente = User.query.get(rep.user_id) if rep.user_id else None
    # Historial de cambios
    historial = []
    for log in AuditLog.query.filter_by(reporte_id=rep.id).order_by(AuditLog.fecha.desc()).all():
        usuario = User.query.get(log.user_id)
        historial.append({
            'fecha': log.fecha.strftime('%Y-%m-%d %H:%M'),
            'usuario': f'{usuario.nombre} {usuario.apellido}' if usuario else '-',
            'tipo_usuario': log.tipo_usuario,
            'estado_anterior': log.estado_anterior,
            'estado_nuevo': log.estado_nuevo,
            'comentario': log.comentario
        })
    data = {
        'reporte': {
            'id': rep.id,
            'fecha': rep.fecha_apertura.strftime('%Y-%m-%d') if rep.fecha_apertura else '-',
            'motivo': rep.motivo if hasattr(rep, 'motivo') else getattr(rep, 'tipo', ''),
            'estado': rep.estado,
            'comentario': rep.comentario if hasattr(rep, 'comentario') else '',
            'impacto': rep.score_impact if hasattr(rep, 'score_impact') else '',
            'monto': rep.monto if hasattr(rep, 'monto') else '',
        },
        'cliente': {
            'id': cliente.id if cliente else None,
            'cedula': cliente.cedula if cliente else '-',
            'nacionalidad': cliente.nacionalidad if cliente else '-',
            'nombre': cliente.nombre if cliente else '-',
            'apellido': cliente.apellido if cliente else '-',
            'email': cliente.email if cliente else '-',
            'telefono': cliente.telefono if cliente else '-',
            'direccion': cliente.direccion if cliente else '-',
            'score': cliente.score if cliente else '-',
            'registrado': bool(cliente and cliente.is_verified),
        } if cliente else None,
        'historial': historial
    }
    return jsonify({'success': True, 'data': data})

@main.route('/api/modificar_reporte/<int:reporte_id>', methods=['POST'])
def api_modificar_reporte(reporte_id):
    from .models import CreditHistory, AuditLog, db, User
    rep = CreditHistory.query.get_or_404(reporte_id)
    data = request.get_json()
    user_id = session.get('user_id')
    tipo_usuario = session.get('tipo', 'empresa')
    estado_anterior = rep.estado
    nuevo_estado = data.get('estado', rep.estado)
    comentario = data.get('comentario', '')
    # No permitir volver a 'pendiente' si ya no lo está
    estados_validos = ['pendiente', 'cerrado', 'aprobado', 'rechazado']
    if nuevo_estado not in estados_validos:
        return jsonify({'success': False, 'error': 'Estado no válido.'}), 400
    if estado_anterior != 'pendiente' and nuevo_estado == 'pendiente':
        return jsonify({'success': False, 'error': 'No se puede volver a pendiente.'}), 400
    # Requiere comentario si cambia de estado
    if estado_anterior != nuevo_estado and not comentario.strip():
        return jsonify({'success': False, 'error': 'Debes ingresar un comentario para el cambio de estado.'}), 400
    rep.motivo = data.get('motivo', rep.motivo)
    rep.comentario = comentario or rep.comentario
    if hasattr(rep, 'monto'):
        rep.monto = data.get('monto', rep.monto)
    rep.estado = nuevo_estado
    db.session.commit()
    # Registrar en AuditLog
    if estado_anterior != nuevo_estado:
        log = AuditLog(
            reporte_id=rep.id,
            user_id=user_id,
            tipo_usuario=tipo_usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            comentario=comentario
        )
        db.session.add(log)
        db.session.commit()
    return jsonify({'success': True, 'message': 'Reporte modificado correctamente.'})

@main.route('/api/descargar_reporte/<int:reporte_id>', methods=['GET'])
def api_descargar_reporte(reporte_id):
    from .models import CreditHistory, User
    rep = CreditHistory.query.get_or_404(reporte_id)
    cliente = User.query.get(rep.user_id) if rep.user_id else None
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    y = 750
    p.setFont('Helvetica-Bold', 16)
    p.drawString(50, y, 'Reporte de Cliente y Crédito')
    y -= 30
    p.setFont('Helvetica', 12)
    p.drawString(50, y, f"Fecha: {rep.fecha_apertura.strftime('%Y-%m-%d') if rep.fecha_apertura else '-'}")
    y -= 20
    if cliente:
        p.drawString(50, y, f'Cliente: {cliente.nombre} {cliente.apellido} ({cliente.nacionalidad}{cliente.cedula})')
        y -= 20
        p.drawString(50, y, f'Email: {cliente.email}')
        y -= 20
        p.drawString(50, y, f'Teléfono: {cliente.telefono}')
        y -= 20
        p.drawString(50, y, f'Dirección: {cliente.direccion}')
        y -= 20
        p.drawString(50, y, f'Score actual: {cliente.score}')
        y -= 30
    p.setFont('Helvetica-Bold', 13)
    p.drawString(50, y, 'Datos del Reporte:')
    y -= 20
    p.setFont('Helvetica', 12)
    p.drawString(50, y, f"Motivo: {rep.motivo if hasattr(rep, 'motivo') else getattr(rep, 'tipo', '')}")
    y -= 20
    p.drawString(50, y, f'Estado: {rep.estado}')
    y -= 20
    if hasattr(rep, 'comentario'):
        p.drawString(50, y, f'Comentario: {rep.comentario}')
        y -= 20
    if hasattr(rep, 'score_impact'):
        p.drawString(50, y, f'Impacto: {rep.score_impact}')
        y -= 20
    if hasattr(rep, 'monto'):
        p.drawString(50, y, f'Monto: {rep.monto}')
        y -= 20
    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f'reporte_{reporte_id}.pdf', mimetype='application/pdf')

# FUNCIONES AUXILIARES

def crear_notificacion(user_id=None, company_id=None, titulo="", mensaje="", tipo="info", accion_url=None):
    """Función para crear notificaciones"""
    notification = Notification(
        user_id=user_id,
        company_id=company_id,
        titulo=titulo,
        mensaje=mensaje,
        tipo=tipo,
        accion_url=accion_url
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def crear_alerta(user_id, tipo, titulo, descripcion, severidad="media"):
    """Función para crear alertas"""
    alerta = Alert(
        user_id=user_id,
        tipo=tipo,
        titulo=titulo,
        descripcion=descripcion,
        severidad=severidad
    )
    db.session.add(alerta)
    db.session.commit()
    return alerta

def registrar_cambio_score(user_id, score_anterior, score_nuevo, motivo, company_id=None, credit_history_id=None):
    """Función para registrar cambios de score"""
    cambio = score_nuevo - score_anterior
    score_change = ScoreChange(
        user_id=user_id,
        score_anterior=score_anterior,
        score_nuevo=score_nuevo,
        cambio=cambio,
        motivo=motivo,
        company_id=company_id,
        credit_history_id=credit_history_id
    )
    db.session.add(score_change)
    db.session.commit()
    return score_change

@main.route('/empresa/clientes')
def clientes_empresa():
    from .models import User, CreditHistory, Appeal
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'empresa' or not user_id:
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('main.dashboard'))
    # Buscar todos los user_id que tengan eventos de CreditHistory o Appeal asociados a la empresa
    credit_user_ids = [c.user_id for c in CreditHistory.query.filter_by(company_id=user_id).all() if c.user_id]
    appeal_user_ids = [a.user_id for a in Appeal.query.join(User, Appeal.user_id == User.id).filter(Appeal.user_id != None).all()]
    all_user_ids = set(credit_user_ids + appeal_user_ids)
    clientes_query = User.query.filter(User.id.in_(all_user_ids)) if all_user_ids else User.query.filter(False)
    q = request.args.get('q', '').strip()
    if q:
        clientes_query = clientes_query.filter((User.cedula.ilike(f"%{q}%")) | (User.nombre.ilike(f"%{q}%")) | (User.apellido.ilike(f"%{q}%")))
    clientes = clientes_query.all()
    return render_template('clientes_empresa.html', clientes=clientes)

@main.route('/empresa/perfil', methods=['GET', 'POST'])
def empresa_perfil():
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'empresa' or not user_id:
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('main.login'))
    
    company = Company.query.get(user_id)
    if not company:
        flash('Empresa no encontrada.', 'danger')
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        # Validar datos requeridos
        name = request.form.get('name', '').strip()
        if not name:
            flash('El nombre de la empresa es obligatorio.', 'danger')
            return render_template('empresa_perfil.html', company=company)
        
        # Actualizar datos de la empresa
        company.name = name
        company.direccion = request.form.get('direccion', '').strip()
        company.telefono = request.form.get('telefono', '').strip()
        company.sector = request.form.get('sector', '').strip()
        
        # Cambiar contraseña si se proporciona
        nueva_password = request.form.get('nueva_password', '').strip()
        if nueva_password:
            if len(nueva_password) < 8:
                flash('La nueva contraseña debe tener al menos 8 caracteres.', 'danger')
                return render_template('empresa_perfil.html', company=company)
            company.password = generate_password_hash(nueva_password)
            flash('Contraseña actualizada correctamente.', 'success')
        
        try:
            db.session.commit()
            flash('Perfil actualizado correctamente. Los cambios se han guardado.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar el perfil. Por favor, intenta nuevamente.', 'danger')
            print(f"Error actualizando perfil empresa: {e}")
    
    return render_template('empresa_perfil.html', company=company)

@main.route('/portal_pagos', methods=['GET', 'POST'])
def portal_pagos():
    from .models import PagoPlan
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'usuario' or not user_id:
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('main.login'))
    if 'pago_plan_data' not in session:
        session['pago_plan_data'] = {}
    paso = int(request.form.get('paso', 1)) if request.method == 'POST' else 1
    pago_data = session['pago_plan_data']
    pagos = PagoPlan.query.filter_by(user_id=user_id).order_by(PagoPlan.created_at.desc()).limit(2).all()
    if request.method == 'POST':
        if paso == 1:
            pago_data['tipo_pago'] = request.form.get('tipo_pago')
            pago_data['moneda'] = request.form.get('moneda')
            pago_data['metodo'] = request.form.get('metodo')
            session['pago_plan_data'] = pago_data
            return render_template('portal_pagos.html', paso=2, tipo='usuario', pago_data=pago_data, pagos=pagos)
        elif paso == 2:
            pago_data['titular'] = request.form.get('titular')
            pago_data['observaciones'] = request.form.get('observaciones')
            pago_data['monto'] = request.form.get('monto')
            pago_data['referencia'] = request.form.get('referencia')
            pago_data['fecha_transferencia'] = request.form.get('fecha_transferencia')
            pago_data['tipo_moneda'] = request.form.get('tipo_moneda')
            session['pago_plan_data'] = pago_data
            return render_template('portal_pagos.html', paso=3, tipo='usuario', pago_data=pago_data, pagos=pagos)
        elif paso == 3:
            imagen = None
            try:
                if 'imagen' in request.files and request.files['imagen'].filename:
                    file = request.files['imagen']
                    filename = secure_filename(file.filename)
                    ruta = os.path.join('static', 'pagos', filename)
                    os.makedirs(os.path.dirname(ruta), exist_ok=True)
                    file.save(ruta)
                    imagen = ruta
                from .models import PagoPlan, db
                pago = PagoPlan(
                    user_id=user_id,
                    plan='pendiente',
                    tipo_pago=pago_data.get('tipo_pago'),
                    moneda=pago_data.get('moneda'),
                    metodo=pago_data.get('metodo'),
                    monto=float(pago_data.get('monto', 0)),
                    titular=pago_data.get('titular'),
                    referencia=pago_data.get('referencia'),
                    fecha_transferencia=pago_data.get('fecha_transferencia'),
                    observaciones=pago_data.get('observaciones'),
                    imagen=imagen,
                    estado='pendiente',
                    created_at=datetime.utcnow()
                )
                db.session.add(pago)
                db.session.commit()
                session.pop('pago_plan_data', None)
                flash('¡Tu pago ha sido registrado exitosamente y está pendiente de aprobación!', 'success')
                return redirect(url_for('main.portal_pagos'))
            except Exception as e:
                flash('Ocurrió un error al registrar tu pago. Intenta nuevamente.', 'danger')
                print(f"Error al guardar pago: {e}")
                return render_template('portal_pagos.html', paso=3, tipo='usuario', pago_data=pago_data, pagos=pagos)
    return render_template('portal_pagos.html', paso=paso, tipo='usuario', pago_data=pago_data, pagos=pagos)

@main.route('/empresa/portal_pagos', methods=['GET', 'POST'])
def empresa_portal_pagos():
    from .models import PagoPlan
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'empresa' or not user_id:
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('main.login'))
    if 'pago_plan_data' not in session:
        session['pago_plan_data'] = {}
    paso = int(request.form.get('paso', 1)) if request.method == 'POST' else 1
    pago_data = session['pago_plan_data']
    pagos = PagoPlan.query.filter_by(company_id=user_id).order_by(PagoPlan.created_at.desc()).limit(2).all()
    if request.method == 'POST':
        if paso == 1:
            pago_data['tipo_pago'] = request.form.get('tipo_pago')
            pago_data['moneda'] = request.form.get('moneda')
            pago_data['metodo'] = request.form.get('metodo')
            session['pago_plan_data'] = pago_data
            return render_template('portal_pagos.html', paso=2, tipo='empresa', pago_data=pago_data, pagos=pagos)
        elif paso == 2:
            pago_data['titular'] = request.form.get('titular')
            pago_data['observaciones'] = request.form.get('observaciones')
            pago_data['monto'] = request.form.get('monto')
            pago_data['referencia'] = request.form.get('referencia')
            pago_data['fecha_transferencia'] = request.form.get('fecha_transferencia')
            pago_data['tipo_moneda'] = request.form.get('tipo_moneda')
            session['pago_plan_data'] = pago_data
            return render_template('portal_pagos.html', paso=3, tipo='empresa', pago_data=pago_data, pagos=pagos)
        elif paso == 3:
            imagen = None
            try:
                if 'imagen' in request.files and request.files['imagen'].filename:
                    file = request.files['imagen']
                    filename = secure_filename(file.filename)
                    ruta = os.path.join('static', 'pagos', filename)
                    os.makedirs(os.path.dirname(ruta), exist_ok=True)
                    file.save(ruta)
                    imagen = ruta
                from .models import PagoPlan, db
                pago = PagoPlan(
                    company_id=user_id,
                    plan='pendiente',
                    tipo_pago=pago_data.get('tipo_pago'),
                    moneda=pago_data.get('moneda'),
                    metodo=pago_data.get('metodo'),
                    monto=float(pago_data.get('monto', 0)),
                    titular=pago_data.get('titular'),
                    referencia=pago_data.get('referencia'),
                    fecha_transferencia=pago_data.get('fecha_transferencia'),
                    observaciones=pago_data.get('observaciones'),
                    imagen=imagen,
                    estado='pendiente',
                    created_at=datetime.utcnow()
                )
                db.session.add(pago)
                db.session.commit()
                session.pop('pago_plan_data', None)
                flash('¡Tu pago ha sido registrado exitosamente y está pendiente de aprobación!', 'success')
                return redirect(url_for('main.empresa_portal_pagos'))
            except Exception as e:
                flash('Ocurrió un error al registrar tu pago. Intenta nuevamente.', 'danger')
                print(f"Error al guardar pago: {e}")
                return render_template('portal_pagos.html', paso=3, tipo='empresa', pago_data=pago_data, pagos=pagos)
    return render_template('portal_pagos.html', paso=paso, tipo='empresa', pago_data=pago_data, pagos=pagos)

@main.route('/mis_pagos', methods=['GET'])
def mis_pagos():
    from .models import PagoPlan
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'usuario' or not user_id:
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('main.login'))
    # Filtros
    mes = request.args.get('mes')
    referencia = request.args.get('referencia', '').strip()
    query = PagoPlan.query.filter_by(user_id=user_id)
    if mes:
        try:
            year, month = map(int, mes.split('-'))
            query = query.filter(db.extract('year', PagoPlan.created_at) == year, db.extract('month', PagoPlan.created_at) == month)
        except:
            pass
    if referencia:
        query = query.filter(PagoPlan.referencia.ilike(f"%{referencia}%"))
    pagos = query.order_by(PagoPlan.created_at.desc()).all()
    return render_template('mis_pagos.html', pagos=pagos, mes=mes, referencia=referencia)

@main.route('/empresa/mis_pagos', methods=['GET'])
def empresa_mis_pagos():
    from .models import PagoPlan
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'empresa' or not user_id:
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('main.login'))
    mes = request.args.get('mes')
    referencia = request.args.get('referencia', '').strip()
    query = PagoPlan.query.filter_by(company_id=user_id)
    if mes:
        try:
            year, month = map(int, mes.split('-'))
            query = query.filter(db.extract('year', PagoPlan.created_at) == year, db.extract('month', PagoPlan.created_at) == month)
        except:
            pass
    if referencia:
        query = query.filter(PagoPlan.referencia.ilike(f"%{referencia}%"))
    pagos = query.order_by(PagoPlan.created_at.desc()).all()
    return render_template('mis_pagos.html', pagos=pagos, mes=mes, referencia=referencia, empresa=True)

@main.route('/admin/pagos', methods=['GET', 'POST'])
def admin_pagos():
    from .models import PagoPlan, User, Company, db
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    user = None
    if user_id:
        user = User.query.get(user_id)
    if not ((tipo == 'admin') or (user and getattr(user, 'is_admin', False))):
        flash('Acceso solo para administradores.', 'danger')
        return redirect(url_for('main.login'))
    # Filtros
    estado = request.args.get('estado', '')
    referencia = request.args.get('referencia', '').strip()
    tipo_cuenta = request.args.get('tipo_cuenta', '')
    mes = request.args.get('mes')
    query = PagoPlan.query
    if estado:
        query = query.filter(PagoPlan.estado == estado)
    if referencia:
        query = query.filter(PagoPlan.referencia.ilike(f"%{referencia}%"))
    if tipo_cuenta == 'empresa':
        query = query.filter(PagoPlan.company_id != None)
    elif tipo_cuenta == 'usuario':
        query = query.filter(PagoPlan.user_id != None, PagoPlan.company_id == None)
    if mes:
        try:
            year, month = map(int, mes.split('-'))
            query = query.filter(db.extract('year', PagoPlan.created_at) == year, db.extract('month', PagoPlan.created_at) == month)
        except:
            pass
    pagos = query.order_by(PagoPlan.created_at.desc()).all()
    # Acciones de aprobar, rechazar, suspender, reactivar
    if request.method == 'POST':
        accion = request.form.get('accion')
        pago_id = request.form.get('pago_id')
        comentario_admin = request.form.get('comentario_admin', '')
        pago = PagoPlan.query.get(pago_id)
        if pago:
            if accion == 'aprobar':
                pago.estado = 'aprobado'
                pago.fecha_aprobacion = db.func.now()
                pago.admin_id = user_id
                pago.comentario_admin = comentario_admin
                # Activar el plan de la empresa/usuario
                if pago.company_id:
                    company = Company.query.get(pago.company_id)
                    if company and pago.plan:
                        company.plan = pago.plan
                        from datetime import datetime, timedelta
                        company.fecha_suscripcion = datetime.utcnow()
                        company.fecha_proximo_pago = company.fecha_suscripcion + timedelta(days=30)
                        flash(f'Pago aprobado y plan {pago.plan} activado para la empresa {company.name}.', 'success')
                    else:
                        flash('Pago aprobado correctamente.', 'success')
                elif pago.user_id:
                    user = User.query.get(pago.user_id)
                    if user and pago.plan:
                        user.plan = pago.plan
                        flash(f'Pago aprobado y plan {pago.plan} activado para el usuario {user.nombre}.', 'success')
                    else:
                        flash('Pago aprobado correctamente.', 'success')
                else:
                    flash('Pago aprobado correctamente.', 'success')
            elif accion == 'rechazar':
                pago.estado = 'rechazado'
                pago.admin_id = user_id
                pago.comentario_admin = comentario_admin
                flash('Pago rechazado.', 'danger')
            elif accion == 'suspender':
                pago.estado = 'suspendido'
                pago.fecha_suspension = db.func.now()
                pago.admin_id = user_id
                pago.comentario_admin = comentario_admin
                flash('Pago suspendido.', 'warning')
            elif accion == 'reactivar':
                pago.estado = 'pendiente'
                pago.fecha_suspension = None
                pago.admin_id = user_id
                pago.comentario_admin = comentario_admin
                flash('Pago reactivado y puesto como pendiente.', 'info')
            db.session.commit()
        return redirect(url_for('main.admin_pagos'))
    return render_template('admin_pagos.html', pagos=pagos, estado=estado, referencia=referencia, tipo_cuenta=tipo_cuenta, mes=mes)

@main.route('/empresa/planes', methods=['GET'])
def empresa_planes():
    from .planes import PLANES
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'empresa' or not user_id:
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('main.login'))
    company = Company.query.get(user_id)
    return render_template('empresa_planes.html', planes=PLANES, company=company)

@main.route('/empresa/confirmar_pago_plan', methods=['GET', 'POST'])
def confirmar_pago_plan():
    from .models import PagoPlan
    from .planes import PLANES
    tipo = session.get('tipo')
    user_id = session.get('user_id')
    if tipo != 'empresa' or not user_id:
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('main.login'))
    plan_seleccionado = request.args.get('plan') or session.get('plan_seleccionado')
    if not plan_seleccionado or plan_seleccionado not in PLANES:
        flash('Debes seleccionar un plan válido.', 'danger')
        return redirect(url_for('main.empresa_planes'))
    session['plan_seleccionado'] = plan_seleccionado
    paso = int(request.form.get('paso', 1)) if request.method == 'POST' else 1
    if 'pago_plan_data' not in session:
        session['pago_plan_data'] = {}
    pago_data = session['pago_plan_data']
    pagos = PagoPlan.query.filter_by(company_id=user_id).order_by(PagoPlan.created_at.desc()).limit(2).all()
    if request.method == 'POST':
        if paso == 1:
            # Solo confirmación visual, pasar a paso 2
            return render_template('confirmar_pago_plan.html', paso=2, plan=PLANES[plan_seleccionado], plan_nombre=plan_seleccionado, pago_data=pago_data, pagos=pagos)
        elif paso == 2:
            pago_data['tipo_pago'] = request.form.get('tipo_pago')
            pago_data['moneda'] = request.form.get('moneda')
            pago_data['metodo'] = request.form.get('metodo')
            session['pago_plan_data'] = pago_data
            return render_template('confirmar_pago_plan.html', paso=3, plan=PLANES[plan_seleccionado], plan_nombre=plan_seleccionado, pago_data=pago_data, pagos=pagos)
        elif paso == 3:
            pago_data['titular'] = request.form.get('titular')
            pago_data['observaciones'] = request.form.get('observaciones')
            pago_data['monto'] = request.form.get('monto')
            pago_data['referencia'] = request.form.get('referencia')
            pago_data['fecha_transferencia'] = request.form.get('fecha_transferencia')
            pago_data['tipo_moneda'] = request.form.get('tipo_moneda')
            session['pago_plan_data'] = pago_data
            return render_template('confirmar_pago_plan.html', paso=4, plan=PLANES[plan_seleccionado], plan_nombre=plan_seleccionado, pago_data=pago_data, pagos=pagos)
        elif paso == 4:
            imagen = None
            try:
                if 'imagen' in request.files and request.files['imagen'].filename:
                    file = request.files['imagen']
                    filename = secure_filename(file.filename)
                    ruta = os.path.join('static', 'pagos', filename)
                    os.makedirs(os.path.dirname(ruta), exist_ok=True)
                    file.save(ruta)
                    imagen = ruta
                from .models import PagoPlan, db
                pago = PagoPlan(
                    company_id=user_id,
                    plan=plan_seleccionado,
                    tipo_pago=pago_data.get('tipo_pago'),
                    moneda=pago_data.get('moneda'),
                    metodo=pago_data.get('metodo'),
                    monto=float(pago_data.get('monto', 0)),
                    titular=pago_data.get('titular'),
                    referencia=pago_data.get('referencia'),
                    fecha_transferencia=pago_data.get('fecha_transferencia'),
                    observaciones=pago_data.get('observaciones'),
                    imagen=imagen,
                    estado='pendiente',
                    created_at=datetime.utcnow()
                )
                db.session.add(pago)
                db.session.commit()
                session.pop('pago_plan_data', None)
                session.pop('plan_seleccionado', None)
                flash('¡Tu pago ha sido registrado exitosamente y está pendiente de aprobación!', 'success')
                return redirect(url_for('main.empresa_mis_pagos'))
            except Exception as e:
                flash('Ocurrió un error al registrar tu pago. Intenta nuevamente.', 'danger')
                print(f"Error al guardar pago: {e}")
                return render_template('confirmar_pago_plan.html', paso=4, plan=PLANES[plan_seleccionado], plan_nombre=plan_seleccionado, pago_data=pago_data, pagos=pagos)
    return render_template('confirmar_pago_plan.html', paso=1, plan=PLANES[plan_seleccionado], plan_nombre=plan_seleccionado, pago_data=pago_data, pagos=pagos)
