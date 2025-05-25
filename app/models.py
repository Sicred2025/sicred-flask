import datetime
from . import db
from datetime import datetime

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    rif = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    plan = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
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


class Appeal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    motivo = db.Column(db.String(255), nullable=False)
    comentario = db.Column(db.Text)
    pruebas = db.Column(db.String(255))  # Ruta al archivo adjunto
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, aprobada, rechazada
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    credit_history_id = db.Column(db.Integer, db.ForeignKey('credit_history.id'))
    cedula = db.Column(db.String(50), nullable=True, index=True)
    nacionalidad = db.Column(db.String(5), nullable=True, index=True)


class ConsultaCredito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class CreditHistory(db.Model):
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
