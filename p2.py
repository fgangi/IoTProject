import cv2
import requests

headers = {
    "Authorization": "Bearer TOKEN",
    "content-type": "application/json",
}

api_endpoints = {
    "encender_luz": "https://danubio.ii.uam.es/api/services/light/turn_on",
    "apagar_luz": "https://danubio.ii.uam.es/api/services/light/turn_off",
}


def data_encender_luz_izquierda(intensidad, temp):
    return {
        "entity_id": "light.lampara_izquierda",
        "brightness_pct": {intensidad},
        "kelvin":{temp}
    }

def data_data_encender_luz_derecha(intensidad, color):
    return {
        "entity_id": "light.lampara_derecha",
        "brightness_pct": {intensidad},
        "rgb_color":{color}
    }

def data_apagar_luz_izquierda():
    return {
        "entity_id": "light.lampara_izquierda",
    }

def data_apagar_luz_derecha():
    return {
        "entity_id": "light.lampara_derecha",
    }


def obtener_datos(endpoint):
    url = api_endpoints.get(endpoint)

    if url:
        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                datos = response.json()
                print(datos)
            else:
                print(f"Error: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

def enviar_datos(endpoint, data):
    url = api_endpoints.get(endpoint)

    if url:
        try:
            response = requests.post(url, headers=headers, json=data)

            if response.status_code == 201:
                datos = response.json()
                print(datos)
            else:
                print(f"Error: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")


def iniciar_camara():
    print("Cámara activada")

# Bucle infinito
if __name__ == "__main__":
    iniciar_camara()
