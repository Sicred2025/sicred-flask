from app import create_app
from app.models import db, User, Company

def check_users():
    app = create_app()
    with app.app_context():
        print("=== USUARIOS EN LA BASE DE DATOS ===")
        users = User.query.all()
        if not users:
            print("No hay usuarios en la base de datos.")
        else:
            for user in users:
                print(f"ID: {user.id}")
                print(f"Email: {user.email}")
                print(f"Nombre: {user.nombre} {user.apellido}")
                print(f"Cédula: {user.cedula}")
                print(f"Admin: {getattr(user, 'is_admin', False)}")
                print(f"Contraseña: {'***' if user.password else 'No definida'}")
                print("-" * 50)
        
        print("\n=== EMPRESAS EN LA BASE DE DATOS ===")
        companies = Company.query.all()
        if not companies:
            print("No hay empresas en la base de datos.")
        else:
            for company in companies:
                print(f"ID: {company.id}")
                print(f"Nombre: {company.name}")
                print(f"Email: {company.email}")
                print(f"RIF: {company.rif}")
                print(f"Contraseña: {'***' if company.password else 'No definida'}")
                print("-" * 50)

if __name__ == '__main__':
    check_users()
