from app import create_app
from app.models import db, Company
from werkzeug.security import generate_password_hash

def add_demo_company():
    app = create_app()
    with app.app_context():
        # Verificar si la empresa ya existe
        existing_company = Company.query.filter_by(email='demo@empresa.com').first()
        if existing_company:
            print("La empresa demo ya existe en la base de datos.")
            return
        
        # Crear la empresa de prueba
        demo_company = Company(
            name='Empresa Demo',
            rif='J-123456789',
            email='demo@empresa.com',
            password=generate_password_hash('demo123'),
            plan='Premium',  # O el plan que prefieras
            is_active=True
        )
        
        db.session.add(demo_company)
        db.session.commit()
        print("Empresa demo creada exitosamente!")
        print(f"Email: demo@empresa.com")
        print(f"Contraseña: demo123")
        print(f"RIF: J-123456789")

if __name__ == '__main__':
    add_demo_company()
