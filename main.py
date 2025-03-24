import cv2
import requests
import mediapipe as mp
import time

# -------------------------------
# Predefined functions (DO NOT MODIFY)
# -------------------------------
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI0NDdlODRkYTExNmI0Yzk2YjIxM2ExMDdhMTY2NmVmMCIsImlhdCI6MTY3ODI3MTU4OSwiZXhwIjoxOTkzNjMxNTg5fQ.-jUvyVsmzQMxrkRd1kLNM_PIH1HTGnzsOzESDWlPukE",
    "content-type": "application/json",
}

api_endpoints = {
    "encender_luz": "https://danubio.ii.uam.es/api/services/light/turn_on",
    "apagar_luz": "https://danubio.ii.uam.es/api/services/light/turn_off",
}

def data_turn_on_left_light(intensity, temp):
    return {
        "entity_id": "light.lampara_izquierda",
        "brightness_pct": intensity,
        "kelvin": temp
    }

def data_turn_on_right_light(intensity, color):
    return {
        "entity_id": "light.lampara_derecha",
        "brightness_pct": intensity,
        "rgb_color": color
    }

def data_turn_off_left_light():
    return {
        "entity_id": "light.lampara_izquierda",
    }

def data_turn_off_right_light():
    return {
        "entity_id": "light.lampara_derecha",
    }

def send_data(endpoint, data):
    url = api_endpoints.get(endpoint)
    if url:
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                response.json()
            else:
                print(f"Error: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

# -------------------------------
# New code for two-handed operation
# -------------------------------

# Global variables
selected_device = "left_light"  # default selected device
right_hand_prev_y = None        # to track vertical movement of the right hand
command_cooldown = 0.5          # cooldown time between commands (in seconds)
last_command_time = time.time() # timestamp of last command
brightness_threshold = 5        # pixel difference threshold for movement

# Initialize MediaPipe with two-hand detection
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

def fingers_up(hand_landmarks):
    """
    Determines which fingers are extended.
    For thumb, compares x-coordinates; for other fingers, compares y-coordinates.
    """
    finger_status = {}
    finger_status["thumb"] = hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x
    finger_status["index"] = hand_landmarks.landmark[8].y < hand_landmarks.landmark[6].y
    finger_status["middle"] = hand_landmarks.landmark[12].y < hand_landmarks.landmark[10].y
    finger_status["ring"] = hand_landmarks.landmark[16].y < hand_landmarks.landmark[14].y
    finger_status["pinky"] = hand_landmarks.landmark[20].y < hand_landmarks.landmark[18].y
    return finger_status

def send_dynamic_command(command):
    """
    Routes the dynamic command to the selected device.
    """
    global selected_device, last_command_time
    if command == "increase_brightness":
        if selected_device == "left_light":
            send_data("encender_luz", data_turn_on_left_light(100, 1800))
        elif selected_device == "right_light":
            send_data("encender_luz", data_turn_on_right_light(100, [0, 0, 255]))
    elif command == "decrease_brightness":
        if selected_device == "left_light":
            send_data("encender_luz", data_turn_on_left_light(10, 1800))
        elif selected_device == "right_light":
            send_data("encender_luz", data_turn_on_right_light(10, [0, 0, 255]))
    elif command == "increase_color":
        if selected_device == "left_light":
            send_data("encender_luz", data_turn_on_left_light(50, 2600))
        elif selected_device == "right_light":
            send_data("encender_luz", data_turn_on_right_light(50, [0, 255, 0]))
    elif command == "decrease_color":
        if selected_device == "left_light":
            send_data("encender_luz", data_turn_on_left_light(50, 1000))
        elif selected_device == "right_light":
            send_data("encender_luz", data_turn_on_right_light(50, [0, 255, 0]))
    elif command == "light_on":
        if selected_device == "left_light":
            send_data("encender_luz", data_turn_on_left_light(50, 1800))
        elif selected_device == "right_light":
            send_data("encender_luz", data_turn_on_right_light(50, [0, 0, 255]))
    elif command == "light_off":
        if selected_device == "left_light":
            send_data("apagar_luz", data_turn_off_left_light())
        elif selected_device == "right_light":
            send_data("apagar_luz", data_turn_off_right_light())
    last_command_time = time.time()

def start_camera():
    global right_hand_prev_y, last_command_time, selected_device
    cap = cv2.VideoCapture(0)
    print("Camera activated")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Mirror the image for a more natural view
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)
            current_time = time.time()

            if results.multi_hand_landmarks and results.multi_handedness:
                for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    # Get the hand label (Left or Right)
                    label = results.multi_handedness[i].classification[0].label
                    status = fingers_up(hand_landmarks)
                    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                    # ---------------------------
                    # Left hand for device selection
                    # ---------------------------
                    if label == "Left":
                        # If the hand is open (all fingers up), select left light
                        if all(status.values()):
                            selected_device = "left_light"
                            cv2.putText(frame, "Selected: Left Light", (10, 30),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                        # If the hand is closed (no fingers up), select right light
                        elif not any(status.values()):
                            selected_device = "right_light"
                            cv2.putText(frame, "Selected: Right Light", (10, 30),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                        # Additional gestures for selection can be added here.
                    
                    # ---------------------------
                    # Right hand for dynamic commands
                    # ---------------------------
                    elif label == "Right":
                        wrist_y = int(hand_landmarks.landmark[0].y * h)
                        # Static gesture: open hand to turn on the light
                        if all(status.values()):
                            if current_time - last_command_time > command_cooldown:
                                cv2.putText(frame, "Turning Light On", (10, 60),
                                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                send_dynamic_command("light_on")
                        # Static gesture: closed fist to turn off the light
                        elif not any(status.values()):
                            if current_time - last_command_time > command_cooldown:
                                cv2.putText(frame, "Turning Light Off", (10, 60),
                                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                                send_dynamic_command("light_off")
                        else:
                            # Dynamic brightness adjustment with only the index finger up
                            if (not status["thumb"] and status["index"] and not status["middle"] and 
                                not status["ring"] and not status["pinky"]):
                                if right_hand_prev_y is not None:
                                    delta_y = wrist_y - right_hand_prev_y
                                    if abs(delta_y) > brightness_threshold and current_time - last_command_time > command_cooldown:
                                        if delta_y < 0:
                                            cv2.putText(frame, "Increasing Brightness", (10, 60),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                            send_dynamic_command("increase_brightness")
                                        elif delta_y > 0:
                                            cv2.putText(frame, "Decreasing Brightness", (10, 60),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                                            send_dynamic_command("decrease_brightness")
                                right_hand_prev_y = wrist_y
                            # Dynamic color adjustment with thumb and index fingers up
                            elif (status["thumb"] and status["index"] and not status["middle"] and 
                                  not status["ring"] and not status["pinky"]):
                                if right_hand_prev_y is not None:
                                    delta_y = wrist_y - right_hand_prev_y
                                    if abs(delta_y) > brightness_threshold and current_time - last_command_time > command_cooldown:
                                        if delta_y < 0:
                                            cv2.putText(frame, "Increasing Color", (10, 60),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                            send_dynamic_command("increase_color")
                                        elif delta_y > 0:
                                            cv2.putText(frame, "Decreasing Color", (10, 60),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                                            send_dynamic_command("decrease_color")
                                right_hand_prev_y = wrist_y

            # Display the currently selected device
            cv2.putText(frame, f"Device: {selected_device}", (10, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.imshow("Gesture Control", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except Exception as e:
        print("Error in main loop:", e)
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    start_camera()
