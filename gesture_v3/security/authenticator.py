import cv2
import face_recognition
import pickle
import os
import time
import numpy as np
import sys

class FaceAuthenticator:
    def __init__(self):
        self.auth_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'security', 'auth.dat')
        self.known_encoding = None
        self.load_profile()
        
        # UI Animation State
        self.scan_line_y = 0
        self.scan_direction = 1
        self.scan_speed = 15

    def load_profile(self):
        if os.path.exists(self.auth_file):
            try:
                with open(self.auth_file, 'rb') as f:
                    self.known_encoding = pickle.load(f)
                print("[SECURITY] Profile loaded.")
            except Exception as e:
                print(f"[SECURITY] Error loading profile: {e}")
        else:
            print("[SECURITY] No registered face found.")

    def draw_hud(self, img, w, h, status="SCANNING", face_loc=None):
        # Colors
        COLOR_CYAN = (255, 255, 0)
        COLOR_RED = (0, 0, 255)
        COLOR_GREEN = (0, 255, 0)
        COLOR_WHITE = (255, 255, 255)
        
        overlay = img.copy()
        
        # 1. Background Grid Effect
        grid_spacing = 60
        for x in range(0, w, grid_spacing):
            cv2.line(overlay, (x, 0), (x, h), (0, 40, 0), 1)
        for y in range(0, h, grid_spacing):
            cv2.line(overlay, (0, y), (w, y), (0, 40, 0), 1)
            
        cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)
        
        # 2. Central Target Zone (The "Space" the user asked for)
        center_x, center_y = w // 2, h // 2
        radius = 180
        
        # Draw segmented circle for Target Zone
        # Segments
        n_segments = 4
        angle_step = 360 / n_segments
        gap = 20
        
        target_color = COLOR_CYAN
        if status == "GRANTED": target_color = COLOR_GREEN
        elif status == "FAILED" or status == "NO_PROFILE": target_color = COLOR_RED
        
        for i in range(n_segments):
            start_angle = i * angle_step + gap
            end_angle = (i + 1) * angle_step - gap
            cv2.ellipse(img, (center_x, center_y), (radius, radius), 0, start_angle, end_angle, target_color, 2)
            cv2.ellipse(img, (center_x, center_y), (radius-10, radius-10), 0, start_angle, end_angle, target_color, 1)

        # 3. Scanning Animation (Vertical Line)
        if status in ["SCANNING", "SEARCHING", "ANALYZING"]:
            cv2.line(img, (0, self.scan_line_y), (w, self.scan_line_y), target_color, 2)
            # Glow
            cv2.line(overlay, (0, self.scan_line_y), (w, self.scan_line_y), target_color, 15)
            cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)
            
            self.scan_line_y += (self.scan_speed * self.scan_direction)
            if self.scan_line_y > h or self.scan_line_y < 0:
                self.scan_direction *= -1

            # Analysis Text near scanner
            cv2.putText(img, f"SCAN_Y: {self.scan_line_y:04d}", (20, self.scan_line_y - 10), cv2.FONT_HERSHEY_PLAIN, 1, target_color, 1)

        # 4. Corner HUD
        margin = 40
        line_len = 80
        
        # Top-Left
        cv2.line(img, (margin, margin), (margin + line_len, margin), target_color, 4)
        cv2.line(img, (margin, margin), (margin, margin + line_len), target_color, 4)
        # Top-Right
        cv2.line(img, (w - margin, margin), (w - margin - line_len, margin), target_color, 4)
        cv2.line(img, (w - margin, margin), (w - margin, margin + line_len), target_color, 4)
        # Bottom-Left
        cv2.line(img, (margin, h - margin), (margin + line_len, h - margin), target_color, 4)
        cv2.line(img, (margin, h - margin), (margin, h - margin - line_len), target_color, 4)
        # Bottom-Right
        cv2.line(img, (w - margin, h - margin), (w - margin - line_len, h - margin), target_color, 4)
        cv2.line(img, (w - margin, h - margin), (w - margin, h - margin - line_len), target_color, 4)

        # 5. Dynamic Status Text
        if status == "GRANTED":
            main_text = "IDENTITY VERIFIED"
            sub_text = "ACCESS GRANTED"
        elif status == "FAILED":
            main_text = "UNKNOWN IDENTITY"
            sub_text = "ACCESS DENIED"
        elif status == "NO_PROFILE":
            main_text = "SYSTEM LOCKED"
            sub_text = "REGISTRATION REQUIRED"
        else: # SCANNING / ANALYZING
            main_text = "BIOMETRIC SCAN"
            sub_text = "ALIGN FACE IN TARGET ZONE"
        
        # Background for text
        cv2.rectangle(img, (0, h - 100), (w, h), (0, 0, 0), -1)
        cv2.line(img, (0, h - 100), (w, h - 100), target_color, 2)
        
        # Draw Text
        text_size = cv2.getTextSize(main_text, cv2.FONT_HERSHEY_DUPLEX, 1.2, 2)[0]
        text_x = (w - text_size[0]) // 2
        cv2.putText(img, main_text, (text_x, h - 60), cv2.FONT_HERSHEY_DUPLEX, 1.2, target_color, 2)
        
        sub_size = cv2.getTextSize(sub_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 1)[0]
        sub_x = (w - sub_size[0]) // 2
        cv2.putText(img, sub_text, (sub_x, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLOR_WHITE, 1)

        # Top Header
        cv2.putText(img, "SECURE GATEWAY V3.1", (margin + 20, margin + 50), cv2.FONT_HERSHEY_PLAIN, 1.2, target_color, 1)

        # 6. Face Highlighting (if detected)
        if face_loc:
            top, right, bottom, left = face_loc
            # Connecting lines to center
            cv2.line(img, (left, top), (center_x, center_y), target_color, 1)
            cv2.line(img, (right, bottom), (center_x, center_y), target_color, 1)
            
            cv2.rectangle(img, (left, top), (right, bottom), target_color, 2)
            cv2.putText(img, "TARGET LOCKED", (left, top - 10), cv2.FONT_HERSHEY_PLAIN, 1, target_color, 1)

    def login_loop(self, cap):
        """
        Blocking loop that prevents system access until face is matched.
        Returns entries to the main loop.
        """
        # Removed the early return for missing profile
        # if self.known_encoding is None: ...
        
        print("[SECURITY] LOCKED. Waiting for face match...")
        
        cv2.namedWindow("SECURITY CHECK", cv2.WND_PROP_FULLSCREEN) 
        
        # Verify capture status
        if not cap.isOpened():
            cap.open(0)

        last_check_time = 0
        check_interval = 0.5 
        
        # Determine initial status
        if self.known_encoding is None:
            status = "NO_PROFILE"
        else:
            status = "SCANNING"
            
        face_location_display = None
        
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape
            
            # 1. Processing (throttled)
            current_time = time.time()
            if current_time - last_check_time > check_interval:
                last_check_time = current_time
                
                # If no profile, we can't match, so just stay in NO_PROFILE state
                if self.known_encoding is not None:
                    # Face Check
                    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                    
                    face_locations = face_recognition.face_locations(rgb_small_frame)
                    
                    if face_locations:
                        status = "ANALYZING"
                        # Just take the first face for UI display purposes (scaled back up)
                        top, right, bottom, left = face_locations[0]
                        face_location_display = (top*4, right*4, bottom*4, left*4)
                        
                        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                        
                        match_found = False
                        for encoding in face_encodings:
                            matches = face_recognition.compare_faces([self.known_encoding], encoding, tolerance=0.5)
                            if True in matches:
                                match_found = True
                                status = "GRANTED"
                                break
                        
                        if match_found:
                            # Show Success UI for a moment
                            self.draw_hud(frame, w, h, status="GRANTED", face_loc=face_location_display)
                            cv2.imshow("SECURITY CHECK", frame)
                            cv2.waitKey(1500) # Pause to show success
                            cv2.destroyWindow("SECURITY CHECK")
                            return True
                        else:
                            status = "FAILED"
                    else:
                        status = "SCANNING"
                        face_location_display = None
                else:
                    status = "NO_PROFILE"

            # 2. Draw UI
            self.draw_hud(frame, w, h, status=status, face_loc=face_location_display)
            
            cv2.imshow("SECURITY CHECK", frame)
            key = cv2.waitKey(1)
            if key == ord('q'):
                print("System Terminated by User.")
                sys.exit(0)
