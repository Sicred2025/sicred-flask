import requests

# Configuración de la API de cédula.com.ve
CEDULA_API_URL = "https://api.cedula.com.ve/api/v1"
CEDULA_API_APP_ID = 957  # <-- Cambia aquí si tu app_id es diferente
CEDULA_API_TOKEN = "d5d4f179a932f19e569f22eacad4ee9c"  # <-- Cambia aquí por tu token real
CEDULA_API_NACIONALIDAD = "V"  # Puedes parametrizarlo si necesitas E (extranjero)

def validar_cedula(cedula, nacionalidad=CEDULA_API_NACIONALIDAD):
    """
    Consulta la API externa de cedula.com.ve para validar una cédula venezolana.
    Retorna el JSON completo si es válida, None si hay error o no existe.
    Ejemplo de uso:
        data = validar_cedula("21489433")
        if data and data.get('success'):
            # Cédula válida, puedes usar data['data']
    """
    try:
        params = {
            'app_id': CEDULA_API_APP_ID,
            'token': CEDULA_API_TOKEN,
            'nacionalidad': nacionalidad,
            'cedula': cedula
        }
        r = requests.get(CEDULA_API_URL, params=params, timeout=7)
        print(f"[CEDULAVE][URL] {r.request.url}")
        print(f"[CEDULAVE][STATUS] {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"[CEDULAVE][RESPUESTA] {data}")
            return data
        else:
            print(f"[CEDULAVE][API] Código de estado: {r.status_code}")
            print(f"[CEDULAVE][RESPUESTA TEXTO] {r.text}")
            return None
    except Exception as e:
        print(f"[CEDULAVE][ERROR] {e}")
        return None

def validar_rif(rif):
    """
    Consulta la API de CedulaVE para validar un RIF venezolano.
    Retorna True si es válido, False si no, None si no se pudo validar.
    """
    try:
        url = f'https://apicvn.megacreativo.com/api/v1/rif/{rif}'
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get('success', False)
        return None
    except Exception as e:
        print(f"[CEDULAVE][ERROR] {e}")
        return None
