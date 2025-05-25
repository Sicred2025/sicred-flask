from app import create_app, db
from app.models import User, Appeal
from datetime import datetime

app = create_app()

with app.app_context():
    user = User.query.filter_by(email='prueba@demo.com').first()
    if not user:
        print('No se encontró el usuario demo con ese correo.')
    else:
        apelacion = Appeal(
            motivo='Motivo de prueba',
            comentario='Esto es una apelación de prueba para ver la notificación visual.',
            pruebas=None,
            estado='pendiente',
            fecha_creacion=datetime.utcnow(),
            user_id=user.id,
            credit_history_id=None
        )
        db.session.add(apelacion)
        db.session.commit()
        print(f'¡Apelación de prueba creada para el usuario {user.email}!')
