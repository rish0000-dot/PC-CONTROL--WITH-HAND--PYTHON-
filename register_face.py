import cv2
import face_recognition
import pickle
import os
import sys
import numpy as np

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

AUTH_FILE = os.path.join(os.path.dirname(__file__), 'gesture_v3', 'security', 'auth.dat')

def register():
    print("=============================================")
    print("   FACE UNLOCK REGISTRATION (FINAL FIX)")
    print("=============================================")
    print("1. Look at the camera.")
    print("2. Align face in the target zone.")
    print("3. Press 'SPACE' to capture.")
    print("4. Press 'Q' to quit.")
    print("=============================================")

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print("ERROR: Could not open camera.")
        return

    # Ensure security directory exists
    os.makedirs(os.path.dirname(AUTH_FILE), exist_ok=True)
    
    scan_y = 0
    scan_dir = 1
    COLOR_CYAN = (255, 255, 0)
    COLOR_RED = (0, 0, 255)

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # Flip and ensure contiguous memory (Critical for dlib)
        frame = cv2.flip(frame, 1)
        
        # UI Rendering
        display_frame = frame.copy()
        h, w, c = display_frame.shape
        
        # 1. Grid
        grid_spacing = 60
        for x in range(0, w, grid_spacing):
            cv2.line(display_frame, (x, 0), (x, h), (0, 40, 0), 1)
        for y in range(0, h, grid_spacing):
            cv2.line(display_frame, (0, y), (w, y), (0, 40, 0), 1)

        # 2. Target Zone
        center_x, center_y = w // 2, h // 2
        cv2.ellipse(display_frame, (center_x, center_y), (180, 230), 0, 0, 360, COLOR_CYAN, 2)
        cv2.putText(display_frame, "ALIGN FACE", (center_x - 70, center_y - 250), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_CYAN, 1)

        # 3. Scanner
        cv2.line(display_frame, (0, scan_y), (w, scan_y), COLOR_CYAN, 2)
        scan_y += (15 * scan_dir)
        if scan_y > h or scan_y < 0: scan_dir *= -1
        
        cv2.imshow("Face Registration", display_frame)

        key = cv2.waitKey(1)
        if key == ord('q'):
            break
        elif key == 32: # SPACE
            # Load OpenCV Face Detector (Haar Cascade) - Robust fallback to bypass dlib detector crash
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            try:
                # 1. Prepare Images
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # 2. Detect using OpenCV (Stable) instead of face_recognition (Crashing)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                
                if len(faces) == 0:
                    print("FAIL: No face detected (OpenCV). Try adjusting position/lighting.")
                    cv2.putText(display_frame, "NO FACE DETECTED", (w//2 - 150, h//2), cv2.FONT_HERSHEY_DUPLEX, 1, COLOR_RED, 2)
                    cv2.imshow("Face Registration", display_frame)
                    cv2.waitKey(500)
                    continue

                # 3. Use the largest face found
                # OpenCV returns (x, y, w, h)
                # face_recognition expects (top, right, bottom, left)
                face = max(faces, key=lambda f: f[2] * f[3])
                x, y, w, h = [int(v) for v in face] # Explicit conversion to int
                
                # Convert format
                css_rect = (y, x + w, y + h, x)
                print(f"DEBUG: Face detected at {css_rect} using OpenCV.")
                
                # Draw the box so user knows it worked
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.imshow("Face Registration", display_frame)
                cv2.waitKey(100)

                # 4. Encode using the detected location
                # We pass the RGB image and the location we found manually
                # This bypasses the crashing detector in dlib
                encodings = face_recognition.face_encodings(rgb, [css_rect])

                if len(encodings) > 0:
                    with open(AUTH_FILE, 'wb') as f:
                        pickle.dump(encodings[0], f)
                    
                    # Success Animation
                    cv2.rectangle(display_frame, (0,0), (w,h), (0,255,0), -1)
                    cv2.addWeighted(display_frame, 0.5, frame, 0.5, 0, display_frame)
                    cv2.putText(display_frame, "SAVED!", (w//2-100, h//2), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 3)
                    cv2.imshow("Face Registration", display_frame)
                    cv2.waitKey(2000)
                    
                    print(f"SUCCESS: Face registered to {AUTH_FILE}")
                    break
                else:
                     print("FAIL: Could not generate encoding from detected face.")

            except Exception as e:
                print(f"CRITICAL ERROR: {e}")
                import traceback
                traceback.print_exc()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    register()
