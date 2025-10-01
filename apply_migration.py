#!/usr/bin/env python3
"""
Script para aplicar la migración de las columnas fecha_suscripcion y fecha_proximo_pago
a la tabla company usando la configuración de Flask.
"""

import os
import sys
from sqlalchemy import create_engine, text

def get_database_url():
    """Obtener la URL de la base de datos desde las variables de entorno."""
    # Intentar obtener desde DATABASE_URL (Railway)
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url
    
    # Si no está disponible, usar configuración local
    return os.getenv('SQLALCHEMY_DATABASE_URI', 'postgresql://username:password@localhost/sicred_db')

def apply_migration():
    """Aplicar la migración para agregar las columnas faltantes."""
    try:
        # Obtener URL de la base de datos
        database_url = get_database_url()
        print(f"🔗 Conectando a la base de datos...")
        
        # Crear conexión a la base de datos
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Verificar si las columnas ya existen
            print("🔍 Verificando columnas existentes...")
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'company' 
                AND column_name IN ('fecha_suscripcion', 'fecha_proximo_pago')
            """))
            
            existing_columns = [row[0] for row in result]
            print(f"Columnas existentes: {existing_columns}")
            
            # Agregar columnas si no existen
            if 'fecha_suscripcion' not in existing_columns:
                print("➕ Agregando columna fecha_suscripcion...")
                connection.execute(text("ALTER TABLE company ADD COLUMN fecha_suscripcion TIMESTAMP"))
                connection.commit()
                print("✅ Columna fecha_suscripcion agregada exitosamente")
            else:
                print("✅ Columna fecha_suscripcion ya existe")
            
            if 'fecha_proximo_pago' not in existing_columns:
                print("➕ Agregando columna fecha_proximo_pago...")
                connection.execute(text("ALTER TABLE company ADD COLUMN fecha_proximo_pago TIMESTAMP"))
                connection.commit()
                print("✅ Columna fecha_proximo_pago agregada exitosamente")
            else:
                print("✅ Columna fecha_proximo_pago ya existe")
        
        print("\n🎉 ¡Migración aplicada exitosamente!")
        print("Las columnas fecha_suscripcion y fecha_proximo_pago han sido agregadas a la tabla company.")
        print("Ahora puedes reiniciar tu aplicación Flask.")
        
    except Exception as e:
        print(f"❌ Error al aplicar la migración: {e}")
        print("\n💡 Posibles soluciones:")
        print("1. Asegúrate de que tu app Flask esté DETENIDA (Ctrl+C)")
        print("2. Verifica que la variable DATABASE_URL esté configurada correctamente")
        print("3. Si usas Railway, asegúrate de que la URL de conexión sea correcta")
        sys.exit(1)

if __name__ == "__main__":
    print("🔧 Aplicando migración para agregar columnas a la tabla company...")
    print("⚠️  IMPORTANTE: Asegúrate de que tu app Flask esté DETENIDA antes de continuar.")
    input("Presiona Enter para continuar...")
    apply_migration() 