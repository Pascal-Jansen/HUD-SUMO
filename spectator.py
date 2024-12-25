import carla
import numpy as np
import cv2
import os
import time
import xml.etree.ElementTree as ET

from collections import deque

class CarlaCameraClient:
    def __init__(self, host='127.0.0.1', port=2000):
        # Initialize the CARLA client and world
        self.client = carla.Client(host, port)
        self.client.set_timeout(10.0)  # Timeout for connection attempts
        self.world = self.client.get_world()
        self.blueprint_library = self.world.get_blueprint_library()
        self.camera = None
        self.vehicle = None
        self.vehicles = []
        self.current_vehicle_index = -1
        self.image_data = None
        self.exit_flag = False

        # Speed-related attributes
        self.speed = 0.0  
        self.current_location = None  
        self.previous_location = None  
        self.current_location_timestamp = None  
        self.previous_location_timestamp = None  
        self.speed_history = deque(maxlen=100)
        self.smoothing_timestamp = None
        self.speed_hud_location = (0.0, 0.0)
        self.speed_number_offset = (0, 0, 0)

        # Camera / HUD configuration
        self.first_person_location = [0.0, 0.0, 0.0]
        self.image_resolution_x = '1920'
        self.image_resolution_y = '1080'
        self.hudname = ''
        self.showInfoOverlay = True

        # HUD icons configuration
        self.hud_area_start = (0.0, 0.0)
        self.icon_path = "icons/"
        self.icons = {
            'icon_stopwatch':      'stopwatch-svgrepo-com.png',
            'icon_battery':        'battery-svgrepo-com.png',
            'icon_calendar':       'calendar-svgrepo-com.png',
            'icon_clock':          'clock-svgrepo-com.png',
            'icon_music_player':   'music-player-svgrepo-com.png',
            'icon_smartphone':     'smartphone-svgrepo-com.png',
            'icon_speaker':        'speaker-svgrepo-com.png',
            'icon_compass':        'compass-svgrepo-com.png',
            'icon_placeholder':    'placeholder-svgrepo-com.png',
            'icon_idea':           'idea-svgrepo-com.png',
            'icon_minus':          'minus-svgrepo-com.png',
            'icon_navigation':     'navigation-svgrepo-com.png'
        }
        # Default positions for up to 11 icons
        self.icon_positions = [(0.0, 0.0)] * 11

        self.show_speed_text = False
        self.show_icon_stopwatch = False
        self.show_icon_battery = False
        self.show_icon_calendar = False
        self.show_icon_clock = False
        self.show_icon_idea = False
        self.show_icon_music_player = False
        self.show_icon_navigation = False
        self.show_icon_smartphone = False
        self.show_icon_speaker = False
        self.show_icon_compass = False
        self.show_icon_minus = False
        self.show_icon_placeholder = False

        # Initially, HUD alpha = 1.0 means fully opaque
        self.hud_alpha = 1.0
        self.iconscale = (90, 90)

        # Initialize OpenCV window
        cv2.namedWindow('Camera Output', cv2.WINDOW_NORMAL)
        
        # Load the numeric HUD configuration from XML
        self.hud_xml_config = self.load_xml_config("hudconfig.xml")

    def load_xml_config(self, xml_file):
        """
        Load the XML configuration file, expecting numeric 
        brightness in [0.0..0.9] and FoV in [30..100] as text.
        """
        config = {}
        if not os.path.isfile(xml_file):
            print(f"[WARNING] {xml_file} not found! Returning empty config.")
            return config

        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        for vehicle in root.findall('Vehicle'):
            type_id = vehicle.get('type_id')
            if type_id:
                HUDName_elem     = vehicle.find('HUDName')
                brightness_elem  = vehicle.find('Brightness')
                frequency_elem   = vehicle.find('Frequency')
                relevance_elem   = vehicle.find('Relevance')
                fov_elem         = vehicle.find('FoV')

                # Convert brightness/FoV to float, defaulting to mid-range
                brightness_val = 0.4  # Fallback if none
                fov_val = 60.0
                if brightness_elem is not None:
                    try:
                        brightness_val = float(brightness_elem.text)
                    except ValueError:
                        print(f"[WARNING] Invalid brightness for {type_id}, using 0.4")

                if fov_elem is not None:
                    try:
                        fov_val = float(fov_elem.text)
                    except ValueError:
                        print(f"[WARNING] Invalid FoV for {type_id}, using 60.0")

                config[type_id] = {
                    'HUDName':   HUDName_elem.text if HUDName_elem is not None else "",
                    'Brightness': brightness_val,
                    'Frequency':  frequency_elem.text if frequency_elem is not None else "average",
                    'Relevance':  relevance_elem.text if relevance_elem is not None else "neutral",
                    'FoV':        fov_val
                }
        return config
    
    def set_xml_config(self, vehicle):
        """Apply numeric brightness/FoV and string-based relevance/frequency to the HUD."""
        if vehicle.type_id in self.hud_xml_config:
            config = self.hud_xml_config[vehicle.type_id]
            self.hudname      = config.get('HUDName', '')
            brightness_val    = config.get('Brightness', 0.4)  # float in [0.0..0.9]
            relevance         = config.get('Relevance', 'neutral')
            frequency         = config.get('Frequency', 'average')
            fov_val           = config.get('FoV', 60.0)  # float in [30..100]
            x = self.hud_area_start[0]
            y = self.hud_area_start[1]

            # Convert brightness -> alpha 
            # For example, brightness=0.0 => alpha=1.0 (fully visible)
            # brightness=0.9 => alpha=0.1 (near-transparent)
            alpha = 1.0 - brightness_val
            self.hud_alpha = max(0.1, alpha)

            # Interpret numeric FoV as small/medium/large
            if fov_val <= 45:
                # small FoV
                self.speed_hud_location = (x, y + 0.1)
                self.iconscale = (60, 60)
                self.speed_number_offset = (20, 55, 0.45)
                self.icon_positions = [
                    (x,     y + 0.05),
                    (x,     y + 0.15),
                    (x - .06, y + 0.1),
                    (x - .06, y + 0.05),
                    (x - .06, y + 0.15),
                    (x,     y + 0.2),
                    (x - .06, y + 0.2),
                    (x,     y),
                    (x - .06, y),
                    (x,     y + 0.25),
                    (x - .06, y + 0.25)
                ]
            elif 45 < fov_val < 75:
                # medium FoV
                self.speed_hud_location = (x, y + 0.1)
                self.speed_number_offset = (33, 84, 0.6)
                self.icon_positions = [
                    (x,     y + 0.05),
                    (x,     y + 0.15),
                    (x - .1, y + 0.1),
                    (x - .1, y + 0.05),
                    (x - .1, y + 0.15),
                    (x,     y + 0.2),
                    (x - .1, y + 0.2),
                    (x,     y),
                    (x - .1, y),
                    (x,     y + 0.25),
                    (x - .1, y + 0.25)
                ]
            else:
                # large FoV
                self.speed_hud_location = (x - 0.05, y + 0.2)
                self.speed_number_offset = (33, 84, 0.6)
                self.icon_positions = [
                    (x - .05, y + 0.1),
                    (x - .05, y + 0.3),
                    (x - .2,  y + 0.2),
                    (x - .2,  y + 0.1),
                    (x - .2,  y + 0.3),
                    (x - .05, y + 0.4),
                    (x - .2,  y + 0.4),
                    (x - .05, y),
                    (x - .2,  y),
                    (x - .05, y + 0.5),
                    (x - .2,  y + 0.5)
                ]

            # Show/hide icons depending on Relevance
            if relevance == "unimportant":
                self.show_speed_text = True
                self.show_icon_stopwatch = True
                self.show_icon_battery = True
                self.show_icon_calendar = True
                self.show_icon_clock = True
                self.show_icon_idea = True
                self.show_icon_music_player = True
                self.show_icon_navigation = True
                self.show_icon_smartphone = True
                self.show_icon_speaker = True
                self.show_icon_compass = True
                self.show_icon_minus = True
                self.show_icon_placeholder = True
            elif relevance == "neutral":
                self.show_speed_text = True
                self.show_icon_stopwatch = True
                self.show_icon_clock = True
                self.show_icon_idea = True
                self.show_icon_navigation = True
                self.show_icon_minus = True
                self.show_icon_battery = True
            elif relevance == "important":
                self.show_speed_text = True
                self.show_icon_stopwatch = True
                self.show_icon_navigation = True
                self.show_icon_minus = True
        else:
            # If no XML config found for this vehicle, reset everything
            self.reset_hud()

    def get_all_vehicles(self):
        """Retrieve all vehicles in the world."""
        self.vehicles = []
        while len(self.vehicles) == 0:
            self.world.wait_for_tick()
            self.vehicles = self.world.get_actors().filter("vehicle.*")
        print(f"Found {len(self.vehicles)} vehicles")

    def clear_old_vehicle(self):
        """Clear the old vehicle and reset locations."""
        if self.camera:
            self.camera.stop()
            self.camera.destroy()
        self.current_location = None
        self.previous_location = None
        self.current_location_timestamp = None
        self.previous_location_timestamp = None
        self.speed_history.clear()
        self.smoothing_timestamp = None
        self.first_person_location = [0.0, 0.0, 0.0]
        self.reset_hud()

    def reset_hud(self):
        """Reset all HUD elements for a new HUD configuration."""
        self.hudname = ''
        self.show_speed_text = False
        self.show_icon_stopwatch = False
        self.show_icon_battery = False
        self.show_icon_calendar = False
        self.show_icon_clock = False
        self.show_icon_idea = False
        self.show_icon_music_player = False
        self.show_icon_navigation = False
        self.show_icon_smartphone = False
        self.show_icon_speaker = False
        self.show_icon_compass = False
        self.show_icon_minus = False
        self.show_icon_placeholder = False
        self.hud_alpha = 1.0
        self.iconscale = (90,90)
        self.icon_positions = []
        self.hud_area_start = (0.0, 0.0)
        self.speed_hud_location = (0.0, 0.0)
        self.speed_number_offset = (0, 0, 0)

    def set_vehicle_configuration(self, vehicle):
        """Set the first-person camera location based on vehicle type."""
        vehicle_name = vehicle.type_id
        if vehicle_name == "vehicle.audi.a2":
            self.first_person_location = [0.2, -0.3, 1.3]
            self.hud_area_start = (0.58, 0.32)
        elif vehicle_name == "vehicle.audi.tt":
            self.first_person_location = [0.0, -0.3, 1.25]
            self.hud_area_start = (0.6, 0.24)
        elif vehicle_name == "vehicle.jeep.wrangler_rubicon":
            self.first_person_location = [-0.3, -0.3, 1.5]
            self.hud_area_start = (0.58, 0.32)
        elif vehicle_name == "vehicle.chevrolet.impala":
            self.first_person_location = [0.1, -0.3, 1.2]
            self.hud_area_start = (0.57, 0.29)
        elif vehicle_name == "vehicle.mini.cooper_s":
            self.first_person_location = [-0.1, -0.35, 1.2]
            self.hud_area_start = (0.53, 0.23)
        elif vehicle_name == "vehicle.mercedes.coupe":
            self.first_person_location = [-0.1, -0.3, 1.25]
            self.hud_area_start = (0.52, 0.28)
        elif vehicle_name == "vehicle.bmw.grandtourer":
            self.first_person_location = [0.0, -0.3, 1.35]
            self.hud_area_start = (0.55, 0.22)
        elif vehicle_name == "vehicle.citroen.c3":
            self.first_person_location = [-0.1, -0.3, 1.3]
            self.hud_area_start = (0.53, 0.32)
        elif vehicle_name == "vehicle.ford.mustang":
            self.first_person_location = [-0.2, -0.3, 1.1]
            self.hud_area_start = (0.52, 0.1)
        elif vehicle_name == "vehicle.volkswagen.t2":
            self.first_person_location = [1.0, -0.3, 1.65]
            self.hud_area_start = (0.58, 0.23)
        elif vehicle_name == "vehicle.lincoln.mkz_2017":
            self.first_person_location = [0.0, -0.3, 1.3]
            self.hud_area_start = (0.58, 0.28)
        elif vehicle_name == "vehicle.seat.leon":
            self.first_person_location = [0.1, -0.3, 1.3]
            self.hud_area_start = (0.65, 0.25)
        elif vehicle_name == "vehicle.nissan.patrol":
            self.first_person_location = [-0.1, -0.3, 1.5]
            self.hud_area_start = (0.58, 0.32)
        else:
            print("Vehicle type not found, using default camera position")
            self.first_person_location = [-0.1, -0.3, 1.3]
            self.hud_area_start = (0.58, 0.32)

    def attach_camera_to_vehicle(self, vehicle):
        """Attach a camera to a given vehicle."""
        self.clear_old_vehicle()
        camera_bp = self.blueprint_library.find('sensor.camera.rgb')
        camera_bp.set_attribute('image_size_x', self.image_resolution_x)
        camera_bp.set_attribute('image_size_y', self.image_resolution_y)
        camera_bp.set_attribute('fov', '90')

        self.set_vehicle_configuration(vehicle)
        camera_transform = carla.Transform(
            carla.Location(x=self.first_person_location[0],
                           y=self.first_person_location[1],
                           z=self.first_person_location[2])
        )
        self.camera = self.world.spawn_actor(camera_bp, camera_transform, attach_to=vehicle)
        self.camera.listen(lambda image: self.process_image(image))
        self.vehicle = vehicle
        print(f"Camera attached to vehicle {vehicle.type_id} at {vehicle.get_location()}")

    def process_image(self, image):
        """Process the image from the camera sensor."""
        array = np.frombuffer(image.raw_data, dtype=np.uint8)
        array = np.reshape(array, (image.height, image.width, 4))
        self.image_data = array.copy()

    def display_camera_output(self):
        """Display the camera output using OpenCV."""
        if self.image_data is not None:
            hud_image = self.image_data.copy()
            self.add_hud(hud_image)
            cv2.imshow('Camera Output', hud_image)

    def get_vehicle_speed(self):
        """Get the speed of the current vehicle (km/h)."""
        if self.vehicle is not None:
            self.current_location = self.vehicle.get_location()
            self.current_location_timestamp = time.perf_counter()

            if self.previous_location is None or self.previous_location_timestamp is None:
                self.previous_location = self.current_location
                self.previous_location_timestamp = self.current_location_timestamp
            else:
                distance = np.sqrt((self.current_location.x - self.previous_location.x) ** 2 +
                                   (self.current_location.y - self.previous_location.y) ** 2 +
                                   (self.current_location.z - self.previous_location.z) ** 2)
                period = self.current_location_timestamp - self.previous_location_timestamp

                current_speed = 3.6 * (distance / period)  # m/s -> km/h
                self.speed_history.append(round(current_speed))

                # Simple smoothing: average of speed_history
                # Use a small threshold so we don't spam-smooth constantly.
                if (not self.smoothing_timestamp or 
                    abs(self.current_location_timestamp - self.smoothing_timestamp) > 0.1):
                    self.smoothing_timestamp = self.current_location_timestamp
                    self.speed = sum(self.speed_history) / len(self.speed_history)

                self.previous_location = self.current_location
                self.previous_location_timestamp = self.current_location_timestamp

    def add_hud(self, image):
        """Overlay icons and speed text on the camera image."""
        height, width, _ = image.shape
        
        # Show icons that are True
        poscount = 0
        for icon_name, filename in self.icons.items():
            if getattr(self, f'show_{icon_name}', False):
                icon = cv2.imread(os.path.join(self.icon_path, filename), cv2.IMREAD_UNCHANGED)
                icon = cv2.resize(icon, self.iconscale)
                if icon_name == 'icon_stopwatch':
                    # Special position for speedometer icon
                    abs_position = (
                        int(height * self.speed_hud_location[0]),
                        int(width  * self.speed_hud_location[1])
                    )
                else:
                    abs_position = (
                        int(height * self.icon_positions[poscount][0]),
                        int(width  * self.icon_positions[poscount][1])
                    )
                    poscount += 1
                self.overlay_icon(image, icon, abs_position)

        # Speed text
        self.get_vehicle_speed()
        speed_text = f"{round(self.speed)}"

        font         = cv2.FONT_HERSHEY_SIMPLEX
        fontScale    = self.speed_number_offset[2]
        color        = (0, 0, 0)
        thickness    = 1

        org = (
            int(width  * self.speed_hud_location[1] + self.speed_number_offset[0]),
            int(height * self.speed_hud_location[0] + self.speed_number_offset[1])
        )

        cv2.putText(image, speed_text, org, font, fontScale, color, thickness, cv2.LINE_AA)

        if self.vehicle:
            vehicle_name_arr   = self.vehicle.type_id.split(".")
            if len(vehicle_name_arr) > 2:
                vehicle_name_text = f"Vehicle type: {vehicle_name_arr[1].capitalize()} {vehicle_name_arr[2]}"
            else:
                vehicle_name_text = f"Vehicle type: {self.vehicle.type_id}"

            hudname_text = f"HUD Name: {self.hudname}"

            if self.showInfoOverlay:
                text_size_vehicle = cv2.getTextSize(vehicle_name_text, font, 1, 1)[0]
                text_x = width // 2 - text_size_vehicle[0] // 2

                cv2.putText(
                    image, 
                    hudname_text, 
                    (text_x, 25), 
                    font, 
                    1, 
                    (255, 255, 255), 
                    1, 
                    cv2.LINE_AA
                )
                cv2.putText(
                    image, 
                    vehicle_name_text, 
                    (text_x, 55), 
                    font, 
                    1, 
                    (255, 255, 255), 
                    1, 
                    cv2.LINE_AA
                )

    def overlay_icon(self, image, icon, position):
        """Overlay an RGBA icon onto the image at the given position, factoring in hud_alpha."""
        y, x = position
        h, w = icon.shape[:2]

        # Clipping if the icon is out of bounds
        if y + h > image.shape[0] or x + w > image.shape[1]:
            return  # or clip to the available area

        if icon.shape[2] == 4:  # If icon has an alpha channel
            alpha_s = (icon[:, :, 3] / 255.0) * self.hud_alpha
            alpha_l = 1.0 - alpha_s
            for c in range(3):
                image[y:y+h, x:x+w, c] = alpha_s * icon[:, :, c] + alpha_l * image[y:y+h, x:x+w, c]
        else:
            # No alpha channel, do a simpler overlay
            for c in range(3):
                image[y:y+h, x:x+w, c] = (
                    self.hud_alpha * icon[:, :, c] + (1.0 - self.hud_alpha) * image[y:y+h, x:x+w, c]
                )

    def switch_vehicle(self):
        """Switch to the next available vehicle."""
        self.get_all_vehicles()
        if not self.vehicles:
            print("No vehicles available to switch.")
            return

        num_vehicles = len(self.vehicles)
        self.current_vehicle_index = (self.current_vehicle_index + 1) % num_vehicles

        while True:
            vehicle = self.vehicles[self.current_vehicle_index]
            try:
                print(f"Switching to vehicle {vehicle.type_id} at {vehicle.get_location()}")
                self.attach_camera_to_vehicle(vehicle)
                self.set_xml_config(vehicle)
                break
            except Exception as e:
                print(f"Error switching to vehicle: {str(e)}")
                print(f"Skipping vehicle {vehicle.type_id} due to error.")
                self.current_vehicle_index = (self.current_vehicle_index + 1) % num_vehicles
                if self.current_vehicle_index == 0:
                    print("No valid vehicles found to switch to.")
                    self.exit_flag = True
                    return

    def run(self):
        """Run the main loop to display camera output and switch vehicles."""
        self.switch_vehicle()
        print("Press 'n' to switch to the next vehicle. Press 'o' to toggle overlay. Press 'q' to quit.")
        while not self.exit_flag:
            if (self.vehicle and 
                self.vehicle.get_location().x == 0.0 and 
                self.vehicle.get_location().y == 0.0 and 
                self.vehicle.get_location().z == 0.0):
                print("Vehicle finished or was removed—switching to next vehicle.")
                self.switch_vehicle()

            self.display_camera_output()
            key = cv2.waitKey(1) & 0xFF
            if key == ord('n'):
                print("Switching vehicle...")
                self.switch_vehicle()
            elif key == ord('o'):
                self.showInfoOverlay = not self.showInfoOverlay
                print(f"Overlay toggled -> {self.showInfoOverlay}")
            elif key == ord('q'):
                print("Exiting...")
                self.exit_flag = True
            elif cv2.getWindowProperty('Camera Output', cv2.WND_PROP_VISIBLE) < 1:
                print("Window closed by user.")
                self.exit_flag = True

        self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        print("Cleaning up resources...")
        if self.camera:
            self.camera.stop()
            self.camera.destroy()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    try:
        client = CarlaCameraClient()
        client.run()
    except Exception as e:
        print(f"An error occurred: {e}")
        exit()
    if client:
        client.cleanup()
