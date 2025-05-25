class Plan:
    BRONCE = 'bronce'
    PLATA = 'plata'
    ORO = 'oro'
    DIAMANTE = 'diamante'

PLANES = {
    Plan.BRONCE: {
        'nombre': 'Plan Bronce',
        'precio': 0,
        'descripcion': 'Consultas simples (2/mes), gráfica básica, registro gratuito.'
    },
    Plan.PLATA: {
        'nombre': 'Plan Plata',
        'precio': 8,
        'descripcion': 'Gráfica completa, cuentas abiertas/cerradas, reportes en mora, apelación.'
    },
    Plan.ORO: {
        'nombre': 'Plan Oro',
        'precio': 20,
        'descripcion': 'Todo lo de Plata. Precio preferencial trimestral.'
    },
    Plan.DIAMANTE: {
        'nombre': 'Plan Diamante',
        'precio': 70,
        'descripcion': 'Todo lo de Oro. Precio preferencial anual.'
    }
}
