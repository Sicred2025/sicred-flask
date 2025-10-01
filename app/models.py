import datetime
from . import db
from datetime import datetime

class Company(db.Model):
    __tablename__ = 'company'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    rif = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    plan = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    direccion = db.Column(db.String(200))
    telefono = db.Column(db.String(20))
    sector = db.Column(db.String(100))
    consultas_realizadas_mes = db.Column(db.Integer, default=0)
    ultima_consulta = db.Column(db.DateTime)
    is_verified = db.Column(db.Boolean, default=False)
    fecha_suscripcion = db.Column(db.DateTime)
    fecha_proximo_pago = db.Column(db.DateTime)

class User(db.Model):
    __tablename__ = 'users'  # 👈 Solución clave

    id = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.String(50), nullable=False, index=True)
    nacionalidad = db.Column(db.String(5), nullable=False, index=True, default='V')
    nombre = db.Column(db.String(120), nullable=False)
    apellido = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    score = db.Column(db.Integer, default=450)
    plan = db.Column(db.String(50))
    consultas_realizadas_mes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    direccion = db.Column(db.String(200))
    telefono = db.Column(db.String(20))
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    fecha_nacimiento = db.Column(db.Date)
    genero = db.Column(db.String(10))
    estado_civil = db.Column(db.String(20))
    ocupacion = db.Column(db.String(100))
    ingresos_mensuales = db.Column(db.Float)
    ultima_consulta = db.Column(db.DateTime)
    is_verified = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='activo')

class Appeal(db.Model):
    __tablename__ = 'appeal'

    id = db.Column(db.Integer, primary_key=True)
    motivo = db.Column(db.String(255), nullable=False)
    comentario = db.Column(db.Text)
    pruebas = db.Column(db.String(255))  # Ruta al archivo adjunto
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, aprobada, rechazada
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 👈 corregido
    credit_history_id = db.Column(db.Integer, db.ForeignKey('credit_history.id'))
    cedula = db.Column(db.String(50), nullable=True, index=True)
    nacionalidad = db.Column(db.String(5), nullable=True, index=True)
    fecha_resolucion = db.Column(db.DateTime)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comentario_admin = db.Column(db.Text)
    prioridad = db.Column(db.String(20), default='normal')

class ConsultaCredito(db.Model):
    __tablename__ = 'consulta_credito'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 👈 corregido
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    tipo_consulta = db.Column(db.String(50), default='completa')
    resultado_score = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))

class CreditHistory(db.Model):
    __tablename__ = 'credit_history'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.String(50), nullable=False)
    monto = db.Column(db.Float, default=0)
    fecha_apertura = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_cierre = db.Column(db.DateTime)
    score_impact = db.Column(db.Integer, default=0)
    comentario = db.Column(db.String(255))
    motivo = db.Column(db.String(255))
    pruebas = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 👈 corregido
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    categoria = db.Column(db.String(50))
    institucion = db.Column(db.String(100))
    plazo_meses = db.Column(db.Integer)
    tasa_interes = db.Column(db.Float)
    cuota_mensual = db.Column(db.Float)
    dias_mora = db.Column(db.Integer, default=0)
    fecha_ultimo_pago = db.Column(db.DateTime)
    saldo_actual = db.Column(db.Float)
    user = db.relationship('User', backref='credit_histories')

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    titulo = db.Column(db.String(200), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), default='info')
    leida = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_lectura = db.Column(db.DateTime)
    accion_url = db.Column(db.String(200))

class ScoreChange(db.Model):
    __tablename__ = 'score_changes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    score_anterior = db.Column(db.Integer, nullable=False)
    score_nuevo = db.Column(db.Integer, nullable=False)
    cambio = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(200), nullable=False)
    fecha_cambio = db.Column(db.DateTime, default=datetime.utcnow)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    credit_history_id = db.Column(db.Integer, db.ForeignKey('credit_history.id'))

class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    tipo = db.Column(db.String(50), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    severidad = db.Column(db.String(20), default='media')
    activa = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_resolucion = db.Column(db.DateTime)

class CreditReport(db.Model):
    __tablename__ = 'credit_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    fecha_generacion = db.Column(db.DateTime, default=datetime.utcnow)
    score_final = db.Column(db.Integer, nullable=False)
    cuentas_abiertas = db.Column(db.Integer, default=0)
    cuentas_cerradas = db.Column(db.Integer, default=0)
    cuentas_en_mora = db.Column(db.Integer, default=0)
    total_deuda = db.Column(db.Float, default=0)
    capacidad_credito = db.Column(db.Float, default=0)
    recomendacion = db.Column(db.String(100))
    observaciones = db.Column(db.Text)

class PaymentHistory(db.Model):
    __tablename__ = 'payment_history'
    
    id = db.Column(db.Integer, primary_key=True)
    credit_history_id = db.Column(db.Integer, db.ForeignKey('credit_history.id'))
    fecha_pago = db.Column(db.DateTime, nullable=False)
    monto_pagado = db.Column(db.Float, nullable=False)
    tipo_pago = db.Column(db.String(50))
    estado = db.Column(db.String(20), default='completado')
    referencia = db.Column(db.String(100))
    comentario = db.Column(db.String(255))

class UserSession(db.Model):
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime)
    activa = db.Column(db.Boolean, default=True)
    dispositivo = db.Column(db.String(100))

class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    id = db.Column(db.Integer, primary_key=True)
    reporte_id = db.Column(db.Integer, db.ForeignKey('credit_history.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    tipo_usuario = db.Column(db.String(20))  # 'empresa' o 'admin'
    estado_anterior = db.Column(db.String(20))
    estado_nuevo = db.Column(db.String(20))
    comentario = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)


class PagoPlan(db.Model):
    __tablename__ = 'pago_plan'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    plan = db.Column(db.String(50), nullable=False)
    tipo_pago = db.Column(db.String(50), nullable=False)  # Transferencia, Pago Móvil, Moneda Digital
    moneda = db.Column(db.String(20), nullable=False)     # Bs, USD, USDT, etc.
    metodo = db.Column(db.String(50), nullable=False)     # Airtm, Binance, Zelle, Banco, etc.
    monto = db.Column(db.Float, nullable=False)
    titular = db.Column(db.String(120), nullable=True)
    referencia = db.Column(db.String(100), nullable=False)
    fecha_transferencia = db.Column(db.DateTime, nullable=False)
    observaciones = db.Column(db.Text, nullable=True)
    imagen = db.Column(db.String(255), nullable=True)     # Ruta al comprobante
    estado = db.Column(db.String(20), default='pendiente') # pendiente, aprobado, rechazado, suspendido
    fecha_suscripcion = db.Column(db.DateTime, nullable=True)
    fecha_suspension = db.Column(db.DateTime, nullable=True)
    fecha_aprobacion = db.Column(db.DateTime, nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Admin que aprueba/rechaza
    comentario_admin = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
