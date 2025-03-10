import cv2
import requests
import mediapipe as mp
import time

headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI0NDdlODRkYTExNmI0Yzk2YjIxM2ExMDdhMTY2NmVmMCIsImlhdCI6MTY3ODI3MTU4OSwiZXhwIjoxOTkzNjMxNTg5fQ.-jUvyVsmzQMxrkRd1kLNM_PIH1HTGnzsOzESDWlPukE",
    "content-type": "application/json",
}

api_endpoints = {
    "encender_luz": "https://danubio.ii.uam.es/api/services/light/turn_on",
    "apagar_luz": "https://danubio.ii.uam.es/api/services/light/turn_off",
}


def data_encender_luz_izquierda(intensidad, temp):
    return {
        "entity_id": "light.lampara_izquierda",
        "brightness_pct": intensidad,
        "kelvin": temp
    }

def data_data_encender_luz_derecha(intensidad, color):
    return {
        "entity_id": "light.lampara_derecha",
        "brightness_pct": intensidad,
        "rgb_color": color
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
            else:
                print(f"Error: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

def enviar_datos(endpoint, data):
    url = api_endpoints.get(endpoint)
    if url:
        try:
            response = requests.post(url, headers=headers, json=data)

            if response.status_code == 200:
                datos = response.json()
            else:
                print(f"Error: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")


# Initialize MediaPipe Hands and drawing utilities.
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

# Variables for tracking wrist movement and cooldown.
prev_wrist_y = None
brightness_threshold = 20  # Pixel difference threshold for brightness adjustment.
command_cooldown = 0.5  # Cooldown period in seconds.
last_command_time = time.time() # Timestamp of the last processed command.

# Start video capture.
cap = cv2.VideoCapture(0)

def fingers_up(hand_landmarks):
    """
    Returns a dictionary indicating which fingers are up.
    For thumb, compares x-coordinates (adjust if the image is flipped).
    For other fingers, compares y-coordinates (lower y means higher in the image).
    """
    finger_status = {}
    # Thumb: Check if tip (landmark 4) is to the right of IP joint (landmark 3).
    finger_status["thumb"] = hand_landmarks.landmark[4].x > hand_landmarks.landmark[3].x
    # Other fingers: Check if tip is above (smaller y than) the PIP joint.
    finger_status["index"] = hand_landmarks.landmark[8].y < hand_landmarks.landmark[6].y
    finger_status["middle"] = hand_landmarks.landmark[12].y < hand_landmarks.landmark[10].y
    finger_status["ring"] = hand_landmarks.landmark[16].y < hand_landmarks.landmark[14].y
    finger_status["pinky"] = hand_landmarks.landmark[20].y < hand_landmarks.landmark[18].y
    return finger_status


def iniciar_camara():
    global prev_wrist_y, last_command_time
    print("Cámara activada")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Flip frame for mirror view.
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the frame with MediaPipe Hands.
            results = hands.process(rgb_frame)
            current_time = time.time()
            gesture = None  # For static gestures (light on/off).
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Draw hand landmarks.
                    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    
                    # Determine finger statuses.
                    status = fingers_up(hand_landmarks)
                    
                    # Static gestures:
                    # Light ON: Only index finger is up.
                    if (status["index"] and
                        status["middle"] and status["ring"] and 
                        status["pinky"] and status["thumb"]):
                        gesture = "light_on"
                    # Light OFF: Fist (no fingers up).
                    elif not any(status.values()):
                        gesture = "light_off"
                    else:
                        gesture = None  # No static command detected.
                    
                    # Get wrist's y-coordinate (landmark 0).
                    wrist_y = int(hand_landmarks.landmark[0].y * h)
                    
                    # If no static gesture, use wrist movement to adjust brightness.
                    if gesture is None:
                        if prev_wrist_y is not None:
                            delta_y = wrist_y - prev_wrist_y
                            if abs(delta_y) > brightness_threshold:
                                # Check cooldown before processing brightness adjustment.
                                if current_time - last_command_time > command_cooldown:
                                    if delta_y < 0:
                                        cv2.putText(frame, "Increase Brightness", (10, 60),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                        print("Increase brightness")
                                        enviar_datos("encender_luz", data_encender_luz_izquierda(100, 1800))

                                        last_command_time = current_time
                                    elif delta_y > 0:
                                        cv2.putText(frame, "Decrease Brightness", (10, 60),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                                        print("Decrease brightness")
                                        enviar_datos("encender_luz", data_encender_luz_izquierda(10, 1800))

                                        last_command_time = current_time
                        prev_wrist_y = wrist_y
                    else:
                        # Process static gestures if cooldown is over.
                        if current_time - last_command_time > command_cooldown:
                            if gesture == "light_on":
                                cv2.putText(frame, "Light ON", (10, 30),
                                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                print("Light ON")
                                enviar_datos("encender_luz", data_encender_luz_izquierda(50, 1800))
                                last_command_time = current_time
                            elif gesture == "light_off":
                                cv2.putText(frame, "Light OFF", (10, 30),
                                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                                print("Light OFF")
                                enviar_datos("apagar_luz", data_apagar_luz_izquierda())
                                last_command_time = current_time
                        prev_wrist_y = wrist_y  # Reset wrist position after static gesture.
                    
                    # Process only the first detected hand.
                    break

            # Display the frame.
            cv2.imshow("Gesture Control", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except Exception as e:
            print("Error en el bucle principal:", e)

    cap.release()
    cv2.destroyAllWindows()

# Bucle infinito
if __name__ == "__main__":
    iniciar_camara()
