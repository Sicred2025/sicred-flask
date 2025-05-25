"""
Script para probar la conexión a la base de datos PostgreSQL.
"""
from app import create_app, db

def test_connection():
    """Prueba la conexión a la base de datos configurada."""
    app = create_app()
    
    with app.app_context():
        try:
            # Intentar conectar a la base de datos
            connection = db.engine.connect()
            connection.close()
            print("\n✅ ¡Conexión exitosa a la base de datos PostgreSQL!")
            print("La configuración de la base de datos está correcta.\n")
            
            # Mostrar información sobre las tablas
            print("Tablas disponibles en la base de datos:")
            inspector = db.inspect(db.engine)
            for table_name in inspector.get_table_names():
                print(f"- {table_name}")
                
            return True
        except Exception as e:
            print("\n❌ Error al conectar a la base de datos:")
            print(f"   {str(e)}")
            print("\nVerifica que:")
            print("1. La URL de conexión en .env sea correcta")
            print("2. La base de datos esté en funcionamiento")
            print("3. Tu IP tenga acceso a la base de datos")
            return False

if __name__ == "__main__":
    test_connection()
