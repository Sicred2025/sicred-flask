from app import create_app, db
from app.models import Company
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    email = 'empresa@demo.com'
    if Company.query.filter_by(email=email).first():
        print('La empresa demo ya existe.')
    else:
        empresa = Company(
            name='Empresa Demo',
            rif='J123456789',
            email=email,
            password=generate_password_hash('demo123'),
            plan='bronce',
            is_active=True
        )
        db.session.add(empresa)
        db.session.commit()
        print('Empresa demo creada con éxito.')
