import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

# Datos del usuario de prueba
TEST_USER = {
    'cedula': '12345678',
    'nombre': 'Prueba',
    'apellido': 'Demo',
    'email': 'prueba@demo.com',
    'password': generate_password_hash('demo123'),
    'score': 450,
    'plan': 'Bronce',
    'consultas_realizadas_mes': 0
}

def recreate_db_and_add_user():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        # Crear usuario de prueba
        user = User(**TEST_USER)
        db.session.add(user)
        db.session.commit()
        print('Base de datos recreada y usuario de prueba agregado.')

if __name__ == '__main__':
    recreate_db_and_add_user()
