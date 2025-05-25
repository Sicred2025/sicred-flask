from app import create_app, db
from app.models import User, Company
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
    'consultas_realizadas_mes': 0,
    'is_admin': False
}

# Datos del usuario administrador
ADMIN_USER = {
    'cedula': '87654321',
    'nacionalidad': 'V',
    'nombre': 'Admin',
    'apellido': 'Sistema',
    'email': 'admin@sicred.com',
    'password': generate_password_hash('AdminSicred123!'),
    'score': 1000,
    'plan': 'Admin',
    'consultas_realizadas_mes': 0,
    'is_admin': True
}

def recreate_db_and_add_users():
    app = create_app()
    with app.app_context():
        # Eliminar todas las tablas
        db.drop_all()
        # Crear todas las tablas
        db.create_all()
        
        # Crear usuario de prueba
        user = User(**TEST_USER)
        db.session.add(user)
        
        # Crear usuario administrador
        admin = User(**ADMIN_USER)
        db.session.add(admin)
        
        # Confirmar los cambios
        db.session.commit()
        
        print('Base de datos recreada exitosamente.')
        print('Usuario de prueba creado:')
        print(f'  Email: {TEST_USER["email"]}')
        print(f'  Contraseña: demo123')
        print('\nUsuario administrador creado:')
        print(f'  Email: {ADMIN_USER["email"]}')
        print(f'  Contraseña: AdminSicred123!')

if __name__ == '__main__':
    recreate_db_and_add_users()
