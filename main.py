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
# New code for mapping left hand to left light and right hand to right light
# -------------------------------

# Global variables for each hand
left_hand_prev_y = None       # Track vertical movement of the left hand
right_hand_prev_y = None      # Track vertical movement of the right hand
command_cooldown_left = 0.5   # Cooldown for left hand commands (seconds)
command_cooldown_right = 0.5  # Cooldown for right hand commands (seconds)
last_command_time_left = time.time()
last_command_time_right = time.time()
brightness_threshold = 5      # Minimum pixel difference to detect movement

# Initialize MediaPipe for two-hand detection
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

def fingers_up(hand_landmarks):
    """
    Determines which fingers are extended.
    Compares x for thumb and y for the other fingers.
    """
    finger_status = {}
    finger_status["thumb"] = hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x
    finger_status["index"] = hand_landmarks.landmark[8].y < hand_landmarks.landmark[6].y
    finger_status["middle"] = hand_landmarks.landmark[12].y < hand_landmarks.landmark[10].y
    finger_status["ring"] = hand_landmarks.landmark[16].y < hand_landmarks.landmark[14].y
    finger_status["pinky"] = hand_landmarks.landmark[20].y < hand_landmarks.landmark[18].y
    return finger_status

def send_dynamic_command_left(command):
    global last_command_time_left
    if command == "increase_brightness":
        send_data("encender_luz", data_turn_on_left_light(100, 1800))
    elif command == "decrease_brightness":
        send_data("encender_luz", data_turn_on_left_light(10, 1800))
    elif command == "light_on":
        send_data("encender_luz", data_turn_on_left_light(50, 1800))
    elif command == "light_off":
        send_data("apagar_luz", data_turn_off_left_light())
    last_command_time_left = time.time()

def send_dynamic_command_right(command):
    global last_command_time_right
    if command == "increase_brightness":
        send_data("encender_luz", data_turn_on_right_light(100, [0, 0, 255]))
    elif command == "decrease_brightness":
        send_data("encender_luz", data_turn_on_right_light(10, [0, 0, 255]))
    elif command == "light_on":
        send_data("encender_luz", data_turn_on_right_light(50, [0, 0, 255]))
    elif command == "light_off":
        send_data("apagar_luz", data_turn_off_right_light())
    last_command_time_right = time.time()

def start_camera():
    global left_hand_prev_y, right_hand_prev_y, last_command_time_left, last_command_time_right
    cap = cv2.VideoCapture(0)
    print("Camera activated")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Mirror the image for a natural view
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)
            current_time = time.time()

            if results.multi_hand_landmarks and results.multi_handedness:
                for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    # Identify if this is the left or right hand
                    label = results.multi_handedness[i].classification[0].label
                    status = fingers_up(hand_landmarks)
                    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                    if label == "Left":
                        # Use left hand to control left light
                        wrist_y = int(hand_landmarks.landmark[0].y * h)
                        # Open hand gesture to turn left light on
                        if all(status.values()):
                            if current_time - last_command_time_left > command_cooldown_left:
                                cv2.putText(frame, "Left Light On", (10, 60),
                                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                send_dynamic_command_left("light_on")
                        # Closed fist to turn left light off
                        elif not any(status.values()):
                            if current_time - last_command_time_left > command_cooldown_left:
                                cv2.putText(frame, "Left Light Off", (10, 60),
                                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                                send_dynamic_command_left("light_off")
                        else:
                            # Adjust brightness with dynamic movement (only index finger up)
                            if (not status["thumb"] and status["index"] and not status["middle"] and
                                not status["ring"] and not status["pinky"]):
                                if left_hand_prev_y is not None:
                                    delta_y = wrist_y - left_hand_prev_y
                                    if abs(delta_y) > brightness_threshold and current_time - last_command_time_left > command_cooldown_left:
                                        if delta_y < 0:
                                            cv2.putText(frame, "Left Light Increase Brightness", (10, 60),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                            send_dynamic_command_left("increase_brightness")
                                        elif delta_y > 0:
                                            cv2.putText(frame, "Left Light Decrease Brightness", (10, 60),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                                            send_dynamic_command_left("decrease_brightness")
                                left_hand_prev_y = wrist_y

                    elif label == "Right":
                        # Use right hand to control right light
                        wrist_y = int(hand_landmarks.landmark[0].y * h)
                        # Open hand gesture to turn right light on
                        if all(status.values()):
                            if current_time - last_command_time_right > command_cooldown_right:
                                cv2.putText(frame, "Right Light On", (10, 100),
                                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                send_dynamic_command_right("light_on")
                        # Closed fist to turn right light off
                        elif not any(status.values()):
                            if current_time - last_command_time_right > command_cooldown_right:
                                cv2.putText(frame, "Right Light Off", (10, 100),
                                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                                send_dynamic_command_right("light_off")
                        else:
                            # Adjust brightness with dynamic movement (only index finger up)
                            if (not status["thumb"] and status["index"] and not status["middle"] and 
                                not status["ring"] and not status["pinky"]):
                                if right_hand_prev_y is not None:
                                    delta_y = wrist_y - right_hand_prev_y
                                    if abs(delta_y) > brightness_threshold and current_time - last_command_time_right > command_cooldown_right:
                                        if delta_y < 0:
                                            cv2.putText(frame, "Right Light Increase Brightness", (10, 100),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                                            send_dynamic_command_right("increase_brightness")
                                        elif delta_y > 0:
                                            cv2.putText(frame, "Right Light Decrease Brightness", (10, 100),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                                            send_dynamic_command_right("decrease_brightness")
                                right_hand_prev_y = wrist_y

            # Display labels for clarity
            cv2.putText(frame, "Left Light (Left Hand)", (10, h - 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(frame, "Right Light (Right Hand)", (10, h - 20),
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
