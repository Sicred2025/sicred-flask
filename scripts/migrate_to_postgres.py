"""
Script para migrar la base de datos a PostgreSQL.
Este script crea todas las tablas necesarias en la base de datos PostgreSQL.
"""
from app import create_app, db
from app.models import User, Company
from werkzeug.security import generate_password_hash

def migrate_database():
    """Migra la base de datos a PostgreSQL."""
    app = create_app()
    
    with app.app_context():
        print("Creando tablas en PostgreSQL...")
        db.create_all()
        print("Tablas creadas correctamente.")
        
        # Verificar si ya existen usuarios
        if User.query.count() == 0:
            print("Creando usuario de prueba...")
            test_user = User(
                cedula='12345678',
                nacionalidad='V',
                nombre='Prueba',
                apellido='Demo',
                email='prueba@demo.com',
                password=generate_password_hash('demo123'),
                is_admin=False
            )
            db.session.add(test_user)
            
            print("Creando usuario administrador...")
            admin_user = User(
                cedula='87654321',
                nacionalidad='V',
                nombre='Admin',
                apellido='Sistema',
                email='admin@sicred.com',
                password=generate_password_hash('AdminSicred123!'),
                is_admin=True
            )
            db.session.add(admin_user)
            
            db.session.commit()
            print("Usuarios creados correctamente.")
        else:
            print("Ya existen usuarios en la base de datos.")
        
        # Verificar si ya existen empresas
        if Company.query.count() == 0:
            print("Creando empresa de prueba...")
            demo_company = Company(
                name='Empresa Demo',
                rif='J-123456789',
                email='demo@empresa.com',
                password=generate_password_hash('demo123'),
                plan='Premium',
                is_active=True
            )
            db.session.add(demo_company)
            db.session.commit()
            print("Empresa creada correctamente.")
        else:
            print("Ya existen empresas en la base de datos.")
        
        # Mostrar las tablas creadas
        print("\nTablas disponibles en la base de datos:")
        inspector = db.inspect(db.engine)
        for table_name in inspector.get_table_names():
            print(f"- {table_name}")

if __name__ == "__main__":
    migrate_database()
