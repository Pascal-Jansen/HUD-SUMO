import tkinter as tk
import subprocess
import xml.etree.ElementTree as ET
from tkinter import messagebox
import os
import random
import time
import calculations
from tkinter import ttk
import xml.etree.cElementTree as ET
import xml.dom.minidom as minidom
from PIL import Image, ImageTk
import traci
import csv
from datetime import datetime
import config

# -----------------------------------------------------------------------
#                          Global / Config
# -----------------------------------------------------------------------
carla_base_dir = config.carla_base_dir
config_script = os.path.join(carla_base_dir, "PythonAPI", "util", "config.py")

sumo_base_dir = os.path.join(carla_base_dir, "Co-Simulation", "Sumo")

maps = {
    "Town01": "{}.sumocfg".format(os.path.join(sumo_base_dir, "examples", "Town01")),
    "Town04": "{}.sumocfg".format(os.path.join(sumo_base_dir, "examples", "Town04")),
    "Town05": "{}.sumocfg".format(os.path.join(sumo_base_dir, "examples", "Town05"))
}

information_frequency = ["minimum", "average", "maximum"]
information_relevance = ["unimportant", "neutral", "important"]

# Full SUMO type IDs
vehicle_type_full = [
    "vehicle.audi.a2", "vehicle.audi.tt",
    "vehicle.chevrolet.impala", "vehicle.mini.cooper_s",
    "vehicle.mercedes.coupe", "vehicle.bmw.grandtourer",
    "vehicle.citroen.c3", "vehicle.ford.mustang",
    "vehicle.volkswagen.t2", "vehicle.lincoln.mkz_2017",
    "vehicle.seat.leon"
]

# Dictionary: short UI name -> full "vehicle.xxx"
vehicle_ui_map = {
    vt.replace("vehicle.", ""): vt for vt in vehicle_type_full
}
available_vehicle_types = list(vehicle_ui_map.keys())
all_vehicle_types = available_vehicle_types[:]

vtypes_xml_path = os.path.join(sumo_base_dir, "examples", "carlavtypes.rou.xml")

# Base definition for "HUD-less" car
base_frame = {
    'HUDname': "HUD-less car",
    'entry': 5,
    'brightness_var': 0.4,   # numeric brightness
    'frequency_var': "none",
    'relevance_var': "none",
    'fov_var': 60.0,         # numeric FoV
    'vehicle_type': "vehicle.nissan.patrol",
    'hud_id': "999"
}

# Used at runtime for mapping each SUMO vehicle ID -> custom vehicle type
vehicle_type_mapping = {}

hud_id_mapping = {}
hud_data = {}
hud_frames = []
string_hud_frames = []
checkbox_vars = []
next_hud_id = 1

# -----------------------------------------------------------------------
#                           Tooltip Class
# -----------------------------------------------------------------------
class ToolTip:
    """A small popup tooltip that appears when hovering over a widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None

    def show_tooltip(self, event=None):
        if not self.widget:
            return
        try:
            x, y, _, _ = self.widget.bbox("insert")
        except tk.TclError:
            x, y = 10, 10
        x += self.widget.winfo_rootx() + 50
        y += self.widget.winfo_rooty() + 20
        if self.tooltip_window:
            self.tooltip_window.destroy()

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            justify="left",
            bg="#ffffe0",
            relief="solid",
            borderwidth=1,
            wraplength=220
        )
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

# -----------------------------------------------------------------------
#                         Utility Functions
# -----------------------------------------------------------------------
def validate_integer_input(value):
    return value.isdigit() and int(value) > 0

def on_validate_input(value, entry):
    if validate_integer_input(value):
        entry.config(bg="white")
    else:
        entry.config(bg="red")
    return True

def update_scrollregion(canvas, container):
    canvas.update_idletasks()
    canvas.config(scrollregion=container.bbox("all"))

def are_all_fields_valid():
    all_valid = True
    for hud in hud_frames:
        val = hud['entry'].get()
        if not val.isdigit() or int(val) <= 0:
            hud['entry'].config(bg="red")
            all_valid = False
        else:
            hud['entry'].config(bg="white")
    return all_valid

# -----------------------------------------------------------------------
# convert_hudFrames
# -----------------------------------------------------------------------
def convert_hudFrames():
    """
    Convert hud_frames -> string_hud_frames by extracting numeric brightness/fov
    and turning them into strings for writing to XML, etc.
    """
    string_hud_frames.clear()
    for hud in hud_frames:
        brightness_val = str(hud['brightness_var'].get())
        fov_val = str(hud['fov_var'].get())

        short_name = hud['vehicle_type'].get()
        full_name = vehicle_ui_map.get(short_name, "vehicle.unknown")

        hud_dict = {
            'HUDname':         hud['HUDname'].get(),
            'entry':           hud['entry'].get(),
            'brightness_var':  brightness_val,
            'frequency_var':   hud['frequency_var'].get(),
            'relevance_var':   hud['relevance_var'].get(),
            'fov_var':         fov_val,
            'vehicle_type':    full_name,
            'hud_id':          str(hud['hud_id'])
        }
        string_hud_frames.append(hud_dict)
    print("Converted hud_frames => string_hud_frames:", string_hud_frames)

# -----------------------------------------------------------------------
# run_simulation
# -----------------------------------------------------------------------
def run_simulation(map_name):
    """
    Start SUMO with FCD-output, run step-by-step, adjusting minGap, collecting data.
    """
    now = datetime.now()
    timestamp = now.strftime("%H-%M-%S_%Y-%m-%d")
    fcd_filename = f'Simulation_data/{map_name}_{timestamp}_fcd_data.xml'

    path = os.path.join(sumo_base_dir, "examples", map_name + ".sumocfg")
    traci.start(["sumo", "-c", path, '--fcd-output', fcd_filename])

    simulation_data = []

    min_gap_mapping = {}
    for vehicle_type, data in hud_data.items():
        mg = data.get("min_Gap", 1.0)
        min_gap_mapping[vehicle_type] = mg

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()

        for vehicle_id in traci.vehicle.getIDList():
            current_gap = traci.vehicle.getMinGap(vehicle_id)
            current_speed = traci.vehicle.getSpeed(vehicle_id) * 3.6
            position = traci.vehicle.getPosition(vehicle_id)
            current_acceleration = traci.vehicle.getAcceleration(vehicle_id)
            distance_traveled = traci.vehicle.getDistance(vehicle_id)
            time_loss = traci.vehicle.getTimeLoss(vehicle_id)
            simTime = traci.simulation.getTime()

            simulation_data.append([
                vehicle_id,
                simTime,
                position[0],
                position[1],
                current_speed,
                current_gap,
                current_acceleration,
                distance_traveled,
                time_loss
            ])

            vtype_for_vehicle = vehicle_type_mapping.get(vehicle_id, "unknown")
            min_gap_for_type = hud_data.get(vtype_for_vehicle, {}).get("min_Gap", 1)
            new_min_gap = max(2.0, (current_speed * 0.5 * min_gap_for_type))
            traci.vehicle.setMinGap(vehicle_id, new_min_gap)

    traci.close()
    save_simulation_data(simulation_data, map_name, timestamp)

def save_simulation_data(simulation_data, map_name, timestamp):
    """
    Save relevant data to CSV, depending on checkboxes.
    """
    if not simulation_data or not isinstance(simulation_data, list):
        print("No simulation data available!")
        return

    if not any(var.get() for var in checkbox_vars):
        print("No simulation data will be saved!")
        return

    fieldnames = []
    if checkbox_vars[0].get(): fieldnames.append('map')
    if checkbox_vars[1].get(): fieldnames.append('vehicle_id')
    if checkbox_vars[2].get(): fieldnames.append('hud_id')
    if checkbox_vars[3].get(): fieldnames.append('simulation_time')
    if checkbox_vars[4].get(): fieldnames.append('vehicle_type')
    if checkbox_vars[5].get(): fieldnames.append('position_x')
    if checkbox_vars[6].get(): fieldnames.append('position_y')
    if checkbox_vars[7].get(): fieldnames.append('current_speed')
    if checkbox_vars[8].get(): fieldnames.append('current_gap')
    if checkbox_vars[9].get(): fieldnames.append('current_acceleration')
    if checkbox_vars[10].get(): fieldnames.append('distance_traveled')
    if checkbox_vars[11].get(): fieldnames.append('time_loss')
    if checkbox_vars[12].get(): fieldnames.append('maxSpeed')
    if checkbox_vars[13].get(): fieldnames.append('speedAdherenceFactor')
    if checkbox_vars[14].get(): fieldnames.append('reactionTime')
    if checkbox_vars[15].get(): fieldnames.append('fatiguenessLevel')
    if checkbox_vars[16].get(): fieldnames.append('awarenessLevel')
    if checkbox_vars[17].get(): fieldnames.append('acceleration')
    if checkbox_vars[18].get(): fieldnames.append('minGapFactor')
    if checkbox_vars[19].get(): fieldnames.append('distractionLevel')
    if checkbox_vars[20].get(): fieldnames.append('brightness')
    if checkbox_vars[21].get(): fieldnames.append('information_frequency')
    if checkbox_vars[22].get(): fieldnames.append('information_relevance')
    if checkbox_vars[23].get(): fieldnames.append('FoV')

    csv_filename = f'Simulation_data/{map_name}_{timestamp}_simulation_data.csv'

    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for entry in simulation_data:
            row_data = {}
            vtype = vehicle_type_mapping.get(entry[0], "unknown")
            hud_data_for_type = hud_data.get(vtype, {})

            hud_name = hud_data_for_type.get('HUDname', 'N/A')
            hud_id_val = hud_id_mapping.get(vtype, "unknown")
            idName = f"{hud_id_val}_{hud_name}"

            if checkbox_vars[0].get():  row_data['map'] = map_name
            if checkbox_vars[1].get():  row_data['vehicle_id'] = entry[0]
            if checkbox_vars[2].get():  row_data['hud_id'] = idName
            if checkbox_vars[3].get():  row_data['simulation_time'] = entry[1]
            if checkbox_vars[4].get():  row_data['vehicle_type'] = vtype
            if checkbox_vars[5].get():  row_data['position_x'] = entry[2]
            if checkbox_vars[6].get():  row_data['position_y'] = entry[3]
            if checkbox_vars[7].get():  row_data['current_speed'] = entry[4]
            if checkbox_vars[8].get():  row_data['current_gap'] = entry[5]
            if checkbox_vars[9].get():  row_data['current_acceleration'] = entry[6]
            if checkbox_vars[10].get(): row_data['distance_traveled'] = entry[7]
            if checkbox_vars[11].get(): row_data['time_loss'] = entry[8]
            if checkbox_vars[12].get(): row_data['maxSpeed'] = hud_data_for_type.get('max_speed', 'N/A')
            if checkbox_vars[13].get(): row_data['speedAdherenceFactor'] = hud_data_for_type.get('speed_factor', 'N/A')
            if checkbox_vars[14].get(): row_data['reactionTime'] = hud_data_for_type.get('reactTime', 'N/A')
            if checkbox_vars[15].get(): row_data['fatiguenessLevel'] = hud_data_for_type.get('fatigueness_level', 'N/A')
            if checkbox_vars[16].get(): row_data['awarenessLevel'] = hud_data_for_type.get('awareness_level', 'N/A')
            if checkbox_vars[17].get(): row_data['acceleration'] = hud_data_for_type.get('accel_factor', 'N/A')
            if checkbox_vars[18].get(): row_data['minGapFactor'] = hud_data_for_type.get('min_Gap', 'N/A')
            if checkbox_vars[19].get(): row_data['distractionLevel'] = hud_data_for_type.get('distraction_level', 'N/A')
            if checkbox_vars[20].get(): row_data['brightness'] = hud_data_for_type.get('brightness', 'N/A')
            if checkbox_vars[21].get(): row_data['information_frequency'] = hud_data_for_type.get('frequency', 'N/A')
            if checkbox_vars[22].get(): row_data['information_relevance'] = hud_data_for_type.get('relevance', 'N/A')
            if checkbox_vars[23].get(): row_data['FoV'] = hud_data_for_type.get('field of view', 'N/A')

            writer.writerow(row_data)

# -----------------------------------------------------------------------
# hudSelection
# -----------------------------------------------------------------------
def hudSelection():
    """
    Convert the user selections to numeric brightness/fov, then call calculations
    to build the hud_data dict for each vehicle type.
    Now returns hud_data, avoiding a NoneType return.
    """
    global hud_data
    hud_data.clear()

    for hud in string_hud_frames:
        brightness_str = hud['brightness_var']
        frequency_str = hud['frequency_var']
        relevance_str = hud['relevance_var']
        fov_str = hud['fov_var']
        vehicle_type = hud['vehicle_type']
        HUDname = hud['HUDname']

        try:
            brightness_val = float(brightness_str)
        except ValueError:
            brightness_val = 0.4

        try:
            fov_val = float(fov_str)
        except ValueError:
            fov_val = 60.0

        # Example: calling calculations from your 'calculations' module:
        distraction_level = calculations.calc_distraction(relevance_str, frequency_str, brightness_val, fov_val)
        fatigueness_level = calculations.calc_fatigueness(relevance_str, frequency_str, brightness_val)
        awareness_level   = calculations.calc_awareness(relevance_str, frequency_str, distraction_level, fatigueness_level, fov_val)
        reactTime         = calculations.calc_ReactTime(distraction_level, fatigueness_level, awareness_level)
        maxSpeed          = calculations.calc_MaxSpeed(awareness_level, fatigueness_level, distraction_level, frequency_str)
        minGap            = calculations.calc_MinGap(distraction_level, fatigueness_level, awareness_level, fov_val)
        speedFactor       = calculations.calc_SpeedAd(fov_val, distraction_level, fatigueness_level, awareness_level, relevance_str, frequency_str)
        accel             = calculations.calc_acceleration(fatigueness_level, distraction_level, awareness_level, relevance_str)

        hud_data[vehicle_type] = {
            'HUDname':           HUDname,
            'distraction_level': distraction_level,
            'fatigueness_level': fatigueness_level,
            'awareness_level':   awareness_level,
            'reactTime':         reactTime,
            'max_speed':         maxSpeed,
            "min_Gap":           minGap,
            'speed_factor':      speedFactor,
            'accel_factor':      accel,
            'brightness':        brightness_val,
            'frequency':         frequency_str,
            'relevance':         relevance_str,
            'field of view':     fov_val
        }
    print("hud_data built =>", hud_data)
    return hud_data

def update_vehicles(xml_file_path, local_data):
    """
    Updates the vehicle types in the .rou.xml with new behaviors (maxSpeed, etc.).
    """
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    for vehicle_type, data in local_data.items():
        if vehicle_type.lower() == "vehicle.nissan.patrol":
            continue

        max_speed     = data['max_speed']
        speedFactor   = data.get('speed_factor', '')
        reactionTime  = data.get('reactTime')
        accelFactor   = data.get('accel_factor')

        for vtype_elem in root.findall('vType'):
            vtype_id = vtype_elem.get('id')
            if vtype_id == vehicle_type:
                vtype_elem.set('maxSpeed', str(max_speed))
                vtype_elem.set('speedFactor', str(speedFactor))
                vtype_elem.set('accel', str(accelFactor))

                driverstate_params = vtype_elem.findall("./param[@key='has.driverstate.device']")
                if driverstate_params:
                    driverstate_params[0].set('value', 'true')
                else:
                    driverstate_param1 = ET.SubElement(vtype_elem, 'param')
                    driverstate_param1.set('key', 'has.driverstate.device')
                    driverstate_param1.set('value', 'true')

                reaction_time_params = vtype_elem.findall("./param[@key='actionStepLength']")
                if reaction_time_params:
                    reaction_time_params[0].set('value', str(reactionTime))
                else:
                    driverstate_param2 = ET.SubElement(vtype_elem, 'param')
                    driverstate_param2.set('key', 'actionStepLength')
                    driverstate_param2.set('value', str(reactionTime))

                color = "#{:02x}{:02x}{:02x}".format(random.randint(0,255), random.randint(0,255), random.randint(0,255))
                vtype_elem.set('color', color)

    tree.write(xml_file_path, encoding='utf-8', xml_declaration=True)

def modify_vehicle_routes(map_name):
    """
    Adjust the vehicle types in the .rou file by user-defined probabilities.
    Also fallback if we get 'vehicle.unknown'.
    """
    original_routes_file = os.path.join(sumo_base_dir, "examples", "rou", map_name + ".rou.xml")
    try:
        tree = ET.parse(original_routes_file)
        root = tree.getroot()

        vehicle_types = []
        probabilities = []
        for hud in string_hud_frames:
            probability = int(hud['entry'])
            short_vtype = hud['vehicle_type']
            # lookup in dictionary. If not found, fallback to 'vehicle.unknown'
            full_vtype = vehicle_ui_map.get(short_vtype, "vehicle.unknown")
            vehicle_types.append(full_vtype)
            probabilities.append(probability)

        for vehicle in root.findall('vehicle'):
            if vehicle_types:
                vehicle_id = vehicle.get('id')
                chosen_type = random.choices(vehicle_types, probabilities)[0]
                # fallback if still vehicle.unknown
                if chosen_type == "vehicle.unknown":
                    # pick a known fallback, e.g. 'vehicle.audi.a2'
                    chosen_type = "vehicle.audi.a2"
                vehicle.set('type', chosen_type)
                vehicle_type_mapping[vehicle_id] = chosen_type

        tree.write(original_routes_file)
    except FileNotFoundError:
        print(f"Couldn't find: {original_routes_file}")

def writeXML(hud_list):
    """
    Writes hudconfig.xml for the spectator client, storing user-chosen strings.
    """
    root = ET.Element("Vehicles")

    for hud in hud_list:
        vehicle_type = hud['vehicle_type']
        brightness_str = hud['brightness_var']
        frequency = hud['frequency_var']
        relevance = hud['relevance_var']
        fov_str = hud['fov_var']
        hud_name = hud['HUDname']

        vehicle_element = ET.SubElement(root, "Vehicle", type_id=vehicle_type)
        ET.SubElement(vehicle_element, "HUDName").text = hud_name
        ET.SubElement(vehicle_element, "Brightness").text = brightness_str
        ET.SubElement(vehicle_element, "Frequency").text = frequency
        ET.SubElement(vehicle_element, "Relevance").text = relevance
        ET.SubElement(vehicle_element, "FoV").text = fov_str

    tree = ET.ElementTree(root)
    xml_file_path = "hudconfig.xml"
    tree.write(xml_file_path, encoding="utf-8", xml_declaration=True)

    dom = minidom.parseString(ET.tostring(root))
    pretty_xml = dom.toprettyxml()
    with open(xml_file_path, "w") as f:
        f.write(pretty_xml)

    return xml_file_path

def start_sumo(selected_sumocfg):
    """
    Start SUMO with GUI if present.
    """
    try:
        subprocess.Popen(['sumo-gui', '-c', selected_sumocfg])
    except FileNotFoundError:
        print("Couldn't start SUMO. Please check if your SUMO path is correct.")

def map_vehicle_type_to_hud_id():
    """
    For each HUD in string_hud_frames, map the SUMO vType to the hud_id in hud_id_mapping.
    """
    hud_id_mapping.clear()
    for hud in string_hud_frames:
        vehicle_type = hud['vehicle_type']
        hud_id = hud['hud_id']
        hud_id_mapping[vehicle_type] = hud_id

def start_simulation():
    """
    Combine all logic to start the sim. Co-Simulation with Carla or SUMO only.
    """
    if not map_list.curselection():
        messagebox.showwarning("No map selected", "Please select a map for the simulation.")
        return

    if not are_all_fields_valid():
        messagebox.showwarning("Invalid Inputs", "Please enter valid integers > 0 for HUD probability!")
        return

    if hudless_var.get() == False and len(hud_frames) == 0:
        messagebox.showwarning("No simulation data", "Please allow simulation without HUD or create HUDs to simulate.")
        return

    selected_index = map_list.curselection()
    # Convert frames => string-based data
    convert_hudFrames()

    if hudless_var.get():
        # Add HUD-less
        string_hud_frames.append(base_frame)
        hud_id_mapping["vehicle.nissan.patrol"] = "999"

    # build hud_id_mapping from string_hud_frames
    map_vehicle_type_to_hud_id()
    # build hud_data with calculations (IMPORTANT: must return hud_data)
    local_data = hudSelection()  
    # update .rou.xml for new behaviors
    update_vehicles(vtypes_xml_path, local_data)

    if selected_index:
        selected_map = map_list.get(selected_index[0])
        # e.g., write an XML for spectator
        writeXML(string_hud_frames)
        # modify routes
        modify_vehicle_routes(selected_map)

        carla_exe = os.path.join(carla_base_dir, "CarlaUE4.exe")

        if spectate_var.get() and simulate_var.get() == False:
            # Carla in RenderOffScreenMode
            try:
                print("Starting CARLA in RenderOffScreenMode")
                subprocess.Popen([carla_exe, "-RenderOffScreen"])
                time.sleep(20)
                print("Running config script:", config_script)
                config_command = ["python", config_script, "--map", selected_map]
                configsubprocess = subprocess.Popen(config_command, cwd=os.path.dirname(config_script))
                configsubprocess.wait()

                sync_script = os.path.join(sumo_base_dir, "run_synchronization.py")
                print("Starting synchronization script with SUMO:", maps[selected_map])
                sync_command = ["python", sync_script, maps[selected_map], "--sumo-gui", "--sync-vehicle-color"]
                subprocess.Popen(sync_command, cwd=os.path.dirname(sync_script))

                try:
                    print("Starting spectator")
                    spectatorpath = "./spectator.py"
                    spectatordir = os.path.dirname(spectatorpath)
                    subprocess.Popen(["python", spectatorpath, spectatordir])
                    print("Spectator started")
                except FileNotFoundError as e:
                    print("Couldn't start the spectator:", e)

                run_simulation(selected_map)

            except FileNotFoundError as e:
                print("Couldn't start the simulation:", e)

        elif simulate_var.get():
            try:
                print("Starting CarlaUE4.exe...")
                subprocess.Popen([carla_exe])
                time.sleep(20)
                print("Running config script:", config_script)
                config_command = ["python", config_script, "--map", selected_map]
                configsubprocess = subprocess.Popen(config_command, cwd=os.path.dirname(config_script))
                configsubprocess.wait()

                sync_script = os.path.join(sumo_base_dir, "run_synchronization.py")
                print("Starting synchronization script with SUMO:", maps[selected_map])
                sync_command = ["python", sync_script, maps[selected_map], "--sumo-gui", "--sync-vehicle-color"]
                subprocess.Popen(sync_command, cwd=os.path.dirname(sync_script))

                if spectate_var.get():
                    try:
                        print("Starting spectator")
                        spectatorpath = "./spectator.py"
                        spectatordir = os.path.dirname(spectatorpath)
                        subprocess.Popen(["python", spectatorpath, spectatordir])
                        print("Spectator started")
                    except FileNotFoundError as e:
                        print("Couldn't start the spectator:", e)

                run_simulation(selected_map)

            except FileNotFoundError as e:
                print("Couldn't start the simulation:", e)

        else:
            # SUMO only
            start_sumo_config = maps[selected_map]
            start_sumo(start_sumo_config)
            run_simulation(selected_map)

def create_hud_frame(hud_id):
    """
    Creates a single HUD frame with brightness/FoV sliders, combobox, etc.
    Returns a dict with references to user selections and widgets.
    """
    hud_num = len(hud_frames) + 1
    frame = tk.Frame(hud_list_frame, bg="white", bd=2, relief="raised")

    # HUD Name
    hudname_entry = tk.Entry(frame, width=22, font=("Helvetica", 14, "bold"))
    hudname_entry.insert(0, f"HUD {hud_num}")
    hudname_entry.grid(row=0, column=0, columnspan=3, padx=10, pady=(5,10), sticky="w")

    # Probability
    lbl_prob = tk.Label(frame, text="HUD Probability:", bg="white", font=("Helvetica", 11))
    lbl_prob.grid(row=1, column=0, pady=5, padx=5, sticky="w")

    prob_var = tk.StringVar()
    prob_entry = tk.Entry(frame, textvariable=prob_var, width=12, font=("Helvetica", 11))
    cmd_val = frame.register(lambda val: on_validate_input(val, prob_entry))
    prob_entry.config(validate="key", validatecommand=(cmd_val, "%P"))
    prob_entry.insert(0, "1")
    prob_entry.grid(row=1, column=1, pady=5, padx=5, sticky="w")

    prob_btn = tk.Button(frame, text="?", width=3)
    prob_btn.grid(row=1, column=2, padx=5)
    prob_tt = ToolTip(prob_btn, "Probability is an integer > 0.\nE.g. '3' => 3x more likely than '1'.")
    prob_btn.bind("<Enter>", lambda e, t=prob_tt: t.show_tooltip())
    prob_btn.bind("<Leave>", lambda e, t=prob_tt: t.hide_tooltip())

    # spacer
    spacer = tk.Label(frame, text="", bg="white", font=("Helvetica", 2))
    spacer.grid(row=2, column=0, columnspan=3)

    # Brightness
    lbl_bright = tk.Label(frame, text="HUD brightness:", bg="white", font=("Helvetica", 11))
    lbl_bright.grid(row=3, column=0, pady=5, padx=5, sticky="w")

    bright_scale = tk.Scale(
        frame, from_=0.0, to=0.9, resolution=0.01,
        orient=tk.HORIZONTAL, length=180,
        bg="white", font=("Helvetica", 10),
        tickinterval=0, showvalue=True
    )
    bright_scale.set(0.4)
    bright_scale.grid(row=3, column=1, pady=5, padx=5, sticky="we")

    bright_btn = tk.Button(frame, text="?", width=3)
    bright_btn.grid(row=3, column=2, padx=5)
    bright_tt = ToolTip(bright_btn, "0.0 => fully opaque,\n0.9 => near-invisible.\nSlider shows current value.")
    bright_btn.bind("<Enter>", lambda e, t=bright_tt: t.show_tooltip())
    bright_btn.bind("<Leave>", lambda e, t=bright_tt: t.hide_tooltip())

    # Frequency
    lbl_freq = tk.Label(frame, text="Information frequency:", bg="white", font=("Helvetica", 11))
    lbl_freq.grid(row=4, column=0, pady=5, padx=5, sticky="w")

    freq_var = tk.StringVar()
    freq_var.set(information_frequency[1])
    freq_menu = ttk.Combobox(frame, textvariable=freq_var, values=information_frequency,
                             state="readonly", font=("Helvetica", 11))
    freq_menu.grid(row=4, column=1, pady=5, padx=5, sticky="we")

    freq_btn = tk.Button(frame, text="?", width=3)
    freq_btn.grid(row=4, column=2, padx=5)
    freq_tt = ToolTip(freq_btn, "Minimum=only when needed,\nMaximum=always displayed.")
    freq_btn.bind("<Enter>", lambda e, t=freq_tt: t.show_tooltip())
    freq_btn.bind("<Leave>", lambda e, t=freq_tt: t.hide_tooltip())

    # Relevance
    lbl_relev = tk.Label(frame, text="Information relevance:", bg="white", font=("Helvetica", 11))
    lbl_relev.grid(row=5, column=0, pady=5, padx=5, sticky="w")

    relev_var = tk.StringVar()
    relev_var.set(information_relevance[1])
    relev_menu = ttk.Combobox(frame, textvariable=relev_var, values=information_relevance,
                              state="readonly", font=("Helvetica", 11))
    relev_menu.grid(row=5, column=1, pady=5, padx=5, sticky="we")

    relev_btn = tk.Button(frame, text="?", width=3)
    relev_btn.grid(row=5, column=2, padx=5)
    relev_tt = ToolTip(relev_btn, "'unimportant' => includes music/weather,\n'important' => essential only.")
    relev_btn.bind("<Enter>", lambda e, t=relev_tt: t.show_tooltip())
    relev_btn.bind("<Leave>", lambda e, t=relev_tt: t.hide_tooltip())

    # spacer
    spacer2 = tk.Label(frame, text="", bg="white", font=("Helvetica", 2))
    spacer2.grid(row=6, column=0, columnspan=3)

    # FoV
    lbl_fov = tk.Label(frame, text="Field of View:", bg="white", font=("Helvetica", 11))
    lbl_fov.grid(row=7, column=0, pady=5, padx=5, sticky="w")

    fov_scale = tk.Scale(
        frame, from_=30, to=100, resolution=1,
        orient=tk.HORIZONTAL, length=180,
        bg="white", font=("Helvetica", 10),
        tickinterval=0, showvalue=True
    )
    fov_scale.set(60)
    fov_scale.grid(row=7, column=1, pady=5, padx=5, sticky="we")

    fov_btn = tk.Button(frame, text="?", width=3)
    fov_btn.grid(row=7, column=2, padx=5)
    fov_tt = ToolTip(fov_btn, "Smaller => near wheel,\nLarger => entire windshield.\nSlider shows current value.")
    fov_btn.bind("<Enter>", lambda e, t=fov_tt: t.show_tooltip())
    fov_btn.bind("<Leave>", lambda e, t=fov_tt: t.hide_tooltip())

    # Vehicle Type
    lbl_vtype = tk.Label(frame, text="Select vehicle type:", bg="white", font=("Helvetica", 11))
    lbl_vtype.grid(row=8, column=0, pady=5, padx=5, sticky="w")

    vtype_var = tk.StringVar()
    if available_vehicle_types:
        vtype_var.set(available_vehicle_types[0])
    else:
        vtype_var.set("NoMoreTypes")

    vtype_menu = ttk.Combobox(frame, textvariable=vtype_var, values=available_vehicle_types,
                              state="readonly", font=("Helvetica", 11))
    vtype_menu.grid(row=8, column=1, pady=5, padx=5, sticky="we")

    remove_btn = tk.Button(frame, text="Remove HUD", bg="#ff6347", fg="white", width=15,
                           font=("Helvetica", 12))
    remove_btn.grid(row=9, column=0, columnspan=3, pady=10)

    new_hud = {
        'frame':         frame,
        'HUDname':       hudname_entry,
        'entry':         prob_entry,
        'brightness_var': bright_scale,
        'frequency_var':  freq_var,
        'relevance_var':  relev_var,
        'fov_var':        fov_scale,
        'vehicle_type':   vtype_var,
        'hud_id':         hud_id
    }
    remove_btn.config(command=lambda: remove_hud(new_hud['hud_id']))

    return new_hud

def add_hud():
    global next_hud_id
    if len(hud_frames) >= len(all_vehicle_types):
        messagebox.showwarning("No available IDs", "No vehicle types left for simulation!")
        return

    hud_obj = create_hud_frame(next_hud_id)
    hud_frames.append(hud_obj)

    short_vtype = hud_obj['vehicle_type'].get()
    if short_vtype in available_vehicle_types:
        available_vehicle_types.remove(short_vtype)

    row_idx = len(hud_frames)
    hud_obj['frame'].grid(row=row_idx, column=0, padx=10, pady=10, sticky="we")

    next_hud_id += 1
    update_scrollregion(main_canvas, hud_list_frame)

def remove_hud(hud_id):
    global hud_frames
    hud_obj = next((h for h in hud_frames if h['hud_id'] == hud_id), None)
    if hud_obj:
        short_vtype = hud_obj['vehicle_type'].get()
        available_vehicle_types.append(short_vtype)
        hud_obj['frame'].destroy()
        hud_frames = [h for h in hud_frames if h['hud_id'] != hud_id]
        update_scrollregion(main_canvas, hud_list_frame)
    else:
        print(f"No HUD found with ID: {hud_id}")

def close_window():
    root.quit()

root = tk.Tk()
root.title("SUMO Simulation Launcher")
root.geometry("800x800")

notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill="both")

# ======================= MAIN TAB ========================
main_tab = ttk.Frame(notebook)
notebook.add(main_tab, text="Main")

main_canvas = tk.Canvas(main_tab, bg="#f0f0f0", highlightthickness=0)
main_scroll = ttk.Scrollbar(main_tab, orient="vertical", command=main_canvas.yview)
main_frame = tk.Frame(main_canvas, bg="#f0f0f0")

def main_configure(e):
    main_canvas.configure(scrollregion=main_canvas.bbox("all"))

main_frame.bind("<Configure>", main_configure)
main_canvas.create_window((0,0), window=main_frame, anchor="nw")
main_canvas.configure(yscrollcommand=main_scroll.set)
main_canvas.pack(side="left", fill="both", expand=True)
main_scroll.pack(side="right", fill="y")

# top area (centered)
top_controls_frame = tk.Frame(main_frame, bg="#f0f0f0")
top_controls_frame.grid(row=0, column=0, pady=10, sticky="n")

map_label = tk.Label(top_controls_frame, text="Select a map:", font=("Helvetica", 14, "bold"), bg="#f0f0f0")
map_label.pack(pady=(0,5))

map_list = tk.Listbox(top_controls_frame, font=("Helvetica", 12), height=5, width=15)
for m in maps:
    map_list.insert(tk.END, m)
map_list.pack(pady=5)

selected_map_index = None
def on_map_select(event):
    global selected_map_index
    sel = map_list.curselection()
    if sel:
        selected_map_index = sel[0]
map_list.bind('<<ListboxSelect>>', on_map_select)

simulate_var = tk.BooleanVar()
simulate_cb = tk.Checkbutton(
    top_controls_frame,
    text="Start co-Simulation with CARLA",
    variable=simulate_var,
    font=("Helvetica", 12),
    bg="#f0f0f0"
)
simulate_cb.pack(pady=5)

spectate_var = tk.BooleanVar()
spectate_cb = tk.Checkbutton(
    top_controls_frame,
    text="Start the CARLA first-person spectator client",
    variable=spectate_var,
    font=("Helvetica", 12),
    bg="#f0f0f0"
)
spectate_cb.pack(pady=5)

hudless_var = tk.BooleanVar()
hudless_cb = tk.Checkbutton(
    top_controls_frame,
    text="Simulate a car that is not using a HUD.\n(HUD probability=5)",
    variable=hudless_var,
    font=("Helvetica", 12),
    bg="#f0f0f0"
)
hudless_cb.pack(pady=5)

# below that: row=1 => hud_list_frame + buttons_frame
hud_list_frame = tk.Frame(main_frame, bg="white", bd=2, relief="sunken")
hud_list_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

buttons_frame = tk.Frame(main_frame, bg="#f0f0f0")
buttons_frame.grid(row=1, column=1, padx=10, pady=10, sticky="n")

btn_add_hud = tk.Button(buttons_frame, text="Add HUD", command=add_hud,
                        bg="#4682b4", fg="white", width=15, font=("Helvetica", 10))
btn_add_hud.pack(pady=5)

btn_start = tk.Button(buttons_frame, text="Start simulation", command=start_simulation,
                      bg="#32cd32", fg="white", width=15, font=("Helvetica", 10))
btn_start.pack(pady=5)

btn_close = tk.Button(buttons_frame, text="Close", command=close_window,
                      bg="#a9a9a9", fg="white", width=15, font=("Helvetica", 10))
btn_close.pack(pady=5)

# ======================= SETTINGS TAB =====================
settings_tab = ttk.Frame(notebook)
notebook.add(settings_tab, text="Settings")

set_canvas = tk.Canvas(settings_tab, bg="white", highlightthickness=0)
set_scroll = ttk.Scrollbar(settings_tab, orient="vertical", command=set_canvas.yview)
set_frame = tk.Frame(set_canvas, bg="white")

def set_configure(e):
    set_canvas.configure(scrollregion=set_canvas.bbox("all"))

set_frame.bind("<Configure>", set_configure)
set_canvas.create_window((0,0), window=set_frame, anchor="nw")
set_canvas.configure(yscrollcommand=set_scroll.set)
set_canvas.pack(side="left", fill="both", expand=True)
set_scroll.pack(side="right", fill="y")

intro_label = tk.Label(
    set_frame,
    text="Here you can enable or disable which data is saved to the CSV.",
    font=("Arial", 12), bg="white"
)
intro_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

checkbox_texts = [
    "Enable saving the map name:",
    "Enable saving the vehicle_id:",
    "Enable saving the hud_id:",
    "Enable saving the simulation_time:",
    "Enable saving the vehicle_type:",
    "Enable saving the position_x of the vehicle:",
    "Enable saving the position_y of the vehicle:",
    "Enable saving the current_speed of the vehicle:",
    "Enable saving the current_gap of the vehicle:",
    "Enable saving the current_acceleration of the vehicle:",
    "Enable saving the distance_traveled by the vehicle:",
    "Enable saving the time_loss the vehicle is experiencing:",
    "Enable saving the calculated maxSpeed of the vehicle:",
    "Enable saving the calculated speedAdherenceFactor of the vehicle:",
    "Enable saving the calculated reactionTime:",
    "Enable saving the calculated fatiguenessLevel:",
    "Enable saving the calculated awarenessLevel:",
    "Enable saving the calculated acceleration:",
    "Enable saving the calculated minGapFactor:",
    "Enable saving the calculated distractionLevel:",
    "Enable saving the selected brightness:",
    "Enable saving the selected information_frequency:",
    "Enable saving the selected information_relevance:",
    "Enable saving the selected FoV:"
]

for i, text in enumerate(checkbox_texts, start=1):
    lbl = tk.Label(set_frame, text=text, bg="white", font=("Helvetica", 10))
    lbl.grid(row=i, column=0, padx=10, pady=5, sticky="w")
    var = tk.BooleanVar(value=True)
    cb = ttk.Checkbutton(set_frame, variable=var)
    cb.grid(row=i, column=1, padx=5, pady=5, sticky="w")
    checkbox_vars.append(var)

# ======================== HELP TAB ========================
help_tab = ttk.Frame(notebook)
notebook.add(help_tab, text="Help")

help_canvas = tk.Canvas(help_tab, bg="white", highlightthickness=0)
help_scroll = ttk.Scrollbar(help_tab, orient="vertical", command=help_canvas.yview)
help_frame = tk.Frame(help_canvas, bg="white")

def help_configure(e):
    help_canvas.configure(scrollregion=help_canvas.bbox("all"))

help_frame.bind("<Configure>", help_configure)
help_canvas.create_window((0,0), window=help_frame, anchor="nw")
help_canvas.configure(yscrollcommand=help_scroll.set)
help_canvas.pack(side="left", fill="both", expand=True)
help_scroll.pack(side="right", fill="y")

help_text = tk.Label(
    help_frame,
    text=(
        "HELP PAGE\n\n"
        "1. Use 'Add HUD' to create new HUD configurations.\n"
        "2. Adjust brightness and FoV via sliders (the current value is shown).\n"
        "3. Probability sets how often that HUD is chosen.\n"
        "4. Frequency and relevance control how/when info is displayed.\n"
        "5. Start the simulation via 'Start simulation' on the main page.\n"
        "6. Use the 'Settings' tab to control what data is saved.\n"
        "Scroll if content is large."
    ),
    bg="white",
    font=("Helvetica", 12),
    wraplength=600,
    justify="left"
)
help_text.pack(padx=10, pady=10, anchor="nw")

# Optionally create some default HUDs
def create_default_huds():
    for _ in range(2):
        add_hud()

create_default_huds()

root.mainloop()
