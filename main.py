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

hud_count = 0

vehicle_type_mapping = {}
hud_data = {}

available_vehicle_types = [
    "vehicle.audi.a2", "vehicle.audi.tt",
    "vehicle.chevrolet.impala", "vehicle.mini.cooper_s", "vehicle.mercedes.coupe",
    "vehicle.bmw.grandtourer", "vehicle.citroen.c3", "vehicle.ford.mustang",
    "vehicle.volkswagen.t2", "vehicle.lincoln.mkz_2017", "vehicle.seat.leon"
]

all_vehicle_types = available_vehicle_types[:]

vtypes_xml_path = os.path.join(sumo_base_dir, "examples", "carlavtypes.rou.xml")

base_frame = {
    'HUDname': "HUD-less car",
    'entry': 5,
    'brightness_var': 0.4,  # float default
    'frequency_var': "none",
    'relevance_var': "none",
    'fov_var': 60.0,        # float default
    'vehicle_type': "vehicle.nissan.patrol",
    'hud_id': "999"
}

hud_id_mapping = {}
objects = []

def are_all_fields_valid():
    all_valid = True
    for hud_frame in hud_frames:
        entry_value = hud_frame['entry'].get()
        if not validate_integer_input(entry_value):
            hud_frame['entry'].config(bg="red")
            all_valid = False
        else:
            hud_frame['entry'].config(bg="white")
    return all_valid

def run_simulation(map):
    """
    Function that handles getting the data from the simulation via Traci 
    and setting the minimal Gap dynamically.
    """
    min_gap_mapping = {}
    for vehicle_type, data in hud_data.items():
        min_gap = data.get("min_Gap")
        min_gap_mapping[vehicle_type] = min_gap

    now = datetime.now()
    timestamp = now.strftime("%H-%M-%S_%Y-%m-%d")

    fcd_filename = f'Simulation_data/{map}_{timestamp}_fcd_data.xml'

    path = os.path.join(sumo_base_dir, "examples", map + ".sumocfg")
    traci.start(["sumo", "-c", path, '--fcd-output', fcd_filename])

    simulation_data = []

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

            vehicle_type = vehicle_type_mapping.get(vehicle_id, "unknown")
            min_gap_for_vehicle_type = hud_data.get(vehicle_type, {}).get("min_Gap", 1)
            # Example logic for dynamic minGap
            new_min_gap = max(2.0, (current_speed * 0.5 * min_gap_for_vehicle_type))
            traci.vehicle.setMinGap(vehicle_id, new_min_gap)

    traci.close()
    save_simulation_data(simulation_data, map, timestamp)

def save_simulation_data(simulation_data, map, timestamp):
    """
    Function that checks which checkboxes are enabled and saves 
    relevant data to a .csv file.
    """
    if not simulation_data or not isinstance(simulation_data, list):
        print("No simulation data available!")
        return
    
    if not any(var.get() for var in checkbox_vars):
        print("No simulation data will be saved!")
        return
    
    fieldnames = []
    # The big block of if checkbox_vars[...] conditions:
    if checkbox_vars[0].get():
        fieldnames.append('map')
    if checkbox_vars[1].get():
        fieldnames.append('vehicle_id')
    if checkbox_vars[2].get():
        fieldnames.append('hud_id')
    if checkbox_vars[3].get():
        fieldnames.append('simulation_time')
    if checkbox_vars[4].get():
        fieldnames.append('vehicle_type')
    if checkbox_vars[5].get():
        fieldnames.append('position_x')
    if checkbox_vars[6].get():
        fieldnames.append('position_y')
    if checkbox_vars[7].get():
        fieldnames.append('current_speed')
    if checkbox_vars[8].get():
        fieldnames.append('current_gap')
    if checkbox_vars[9].get():
        fieldnames.append('current_acceleration')
    if checkbox_vars[10].get():
        fieldnames.append('distance_traveled')
    if checkbox_vars[11].get():
        fieldnames.append('time_loss')
    if checkbox_vars[12].get():
        fieldnames.append('maxSpeed')
    if checkbox_vars[13].get():
        fieldnames.append('speedAdherenceFactor')
    if checkbox_vars[14].get():
        fieldnames.append('reactionTime')
    if checkbox_vars[15].get():
        fieldnames.append('fatiguenessLevel')
    if checkbox_vars[16].get():
        fieldnames.append('awarenessLevel')
    if checkbox_vars[17].get():
        fieldnames.append('acceleration')
    if checkbox_vars[18].get():
        fieldnames.append('minGapFactor')
    if checkbox_vars[19].get():
        fieldnames.append('distractionLevel')
    if checkbox_vars[20].get():
        fieldnames.append('brightness')
    if checkbox_vars[21].get():
        fieldnames.append('information_frequency')
    if checkbox_vars[22].get():
        fieldnames.append('information_relevance')
    if checkbox_vars[23].get():
        fieldnames.append('FoV')

    csv_filename = f'Simulation_data/{map}_{timestamp}_simulation_data.csv'
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for entry in simulation_data:
            row_data = {}
            vehicle_type = vehicle_type_mapping.get(entry[0], "unknown")
            hud_data_for_type = hud_data.get(vehicle_type, {})

            hud_name = hud_data_for_type.get('HUDname', 'N/A')
            hud_id_val = hud_id_mapping.get(vehicle_type, "unknown")
            idName = f"{hud_id_val}_{hud_name}"

            if checkbox_vars[0].get():
                row_data['map'] = map
            if checkbox_vars[1].get():
                row_data['vehicle_id'] = entry[0]
            if checkbox_vars[2].get():
                row_data['hud_id'] = idName
            if checkbox_vars[3].get():
                row_data['simulation_time'] = entry[1]
            if checkbox_vars[4].get():
                row_data['vehicle_type'] = vehicle_type
            if checkbox_vars[5].get():
                row_data['position_x'] = entry[2]
            if checkbox_vars[6].get():
                row_data['position_y'] = entry[3]
            if checkbox_vars[7].get():
                row_data['current_speed'] = entry[4]
            if checkbox_vars[8].get():
                row_data['current_gap'] = entry[5]
            if checkbox_vars[9].get():
                row_data['current_acceleration'] = entry[6]
            if checkbox_vars[10].get():
                row_data['distance_traveled'] = entry[7]
            if checkbox_vars[11].get():
                row_data['time_loss'] = entry[8]
            if checkbox_vars[12].get():
                row_data['maxSpeed'] = hud_data_for_type.get('max_speed', 'N/A')
            if checkbox_vars[13].get():
                row_data['speedAdherenceFactor'] = hud_data_for_type.get('speed_factor', 'N/A')
            if checkbox_vars[14].get():
                row_data['reactionTime'] = hud_data_for_type.get('reactTime', 'N/A')
            if checkbox_vars[15].get():
                row_data['fatiguenessLevel'] = hud_data_for_type.get('fatigueness_level', 'N/A')
            if checkbox_vars[16].get():
                row_data['awarenessLevel'] = hud_data_for_type.get('awareness_level', 'N/A')
            if checkbox_vars[17].get():
                row_data['acceleration'] = hud_data_for_type.get('accel_factor', 'N/A')
            if checkbox_vars[18].get():
                row_data['minGapFactor'] = hud_data_for_type.get('min_Gap', 'N/A')
            if checkbox_vars[19].get():
                row_data['distractionLevel'] = hud_data_for_type.get('distraction_level', 'N/A')
            if checkbox_vars[20].get():
                row_data['brightness'] = hud_data_for_type.get('brightness', 'N/A')
            if checkbox_vars[21].get():
                row_data['information_frequency'] = hud_data_for_type.get('frequency', 'N/A')
            if checkbox_vars[22].get():
                row_data['information_relevance'] = hud_data_for_type.get('relevance', 'N/A')
            if checkbox_vars[23].get():
                row_data['FoV'] = hud_data_for_type.get('field of view', 'N/A')

            writer.writerow(row_data)

string_hud_frames = []

def convert_hudFrames():
    """
    Convert all saved HUD frames to string-based dictionaries (for writing XML, etc.).
    """
    for hud in hud_frames:
        string_hud = {
            'HUDname':       str(hud['HUDname'].get()),
            'entry':         str(hud['entry'].get()),
            # We store brightness/fov as strings for the XML,
            # but they are numeric sliders in the GUI.
            'brightness_var': str(hud['brightness_var'].get()),
            'frequency_var':  str(hud['frequency_var'].get()),
            'relevance_var':  str(hud['relevance_var'].get()),
            'fov_var':        str(hud['fov_var'].get()),
            'vehicle_type':   str(hud['vehicle_type'].get()),
            'hud_id':         str(hud['hud_id'])
        }
        string_hud_frames.append(string_hud)
    print(string_hud_frames)

def map_vehicle_type_to_hud_id():
    for hud in string_hud_frames:
        vehicle_type = hud['vehicle_type']
        hud_id = hud['hud_id']
        hud_id_mapping[vehicle_type] = hud_id

def start_simulation():
    """
    Function that handles the start of the simulation.
    """
    if not map_list.curselection():
        messagebox.showwarning("No map selected", "Please select a map for the simulation.")
        return
    
    if not are_all_fields_valid():
        messagebox.showwarning("Invalid Inputs", "Please enter valid inputs for all the input fields!")
        return
    
    if hudless_var.get() is False and len(hud_frames) == 0:
        messagebox.showwarning("No simulation data", "Please allow simulation without HUD or create HUDs to simulate.")
        return

    selected_index = map_list.curselection()
    global hud_count

    convert_hudFrames()

    if hudless_var.get():
        # Add HUD-less car
        string_hud_frames.append(base_frame)
        hud_id_mapping["vehicle.nissan.patrol"] = "999"

    map_vehicle_type_to_hud_id()

    # Generate hud_data with numeric values
    hud_data = hudSelection()

    # Update vehicles in the .rou.xml file with new behaviors
    update_vehicles(carla_base_dir + r"\Co-Simulation\Sumo\examples\carlavtypes.rou.xml", hud_data)

    if selected_index:
        selected_map = map_list.get(selected_index[0])
        selected_sumocfg = maps[selected_map]

        writeXML(string_hud_frames)
        modify_vehicle_routes(selected_map)

        carla_exe = os.path.join(carla_base_dir, "CarlaUE4.exe")

        if spectate_var.get() and simulate_var.get() == False:
            # Carla in RenderOffScreenMode
            try:
                print("Starting CARLA in RenderOffScreenMode")
                subprocess.Popen([carla_exe, "-RenderOffScreen"])

                time.sleep(20)
                print("Waiting after starting CARLA...")

                print("Starting configuration script: {}".format(config_script))
                config_command = ["python", config_script, "--map", selected_map]
                configsubprocess = subprocess.Popen(config_command, cwd=os.path.dirname(config_script))
                configsubprocess.wait()

                sync_script = os.path.join(sumo_base_dir, "run_synchronization.py")
                print("Starting synchronisation script with SUMO: {}".format(selected_sumocfg))
                sync_command = ["python", sync_script, selected_sumocfg, "--sumo-gui", "--sync-vehicle-color"]
                subprocess.Popen(sync_command, cwd=os.path.dirname(sync_script))

                try:
                    print("Starting spectator")
                    spectatorpath = "./spectator.py"
                    spectatordir = os.path.dirname(spectatorpath)
                    subprocess.Popen(["python", spectatorpath, spectatordir])
                    print("Spectator started")
                except FileNotFoundError as e:
                    print("Couldn't start the spectator", e)

                run_simulation(selected_map)

            except FileNotFoundError as e:
                print("Couldn't start the simulation:", e)

        elif simulate_var.get():
            # Full Carla with rendering
            try:
                print("Starting CarlaUE4.exe...")
                subprocess.Popen([carla_exe])

                time.sleep(20)
                print("Waiting after starting CARLA...")

                print("Starting configuration script: {}".format(config_script))
                config_command = ["python", config_script, "--map", selected_map]
                configsubprocess = subprocess.Popen(config_command, cwd=os.path.dirname(config_script))
                configsubprocess.wait()

                sync_script = os.path.join(sumo_base_dir, "run_synchronization.py")
                print("Starting synchronisation script with SUMO: {}".format(selected_sumocfg))
                sync_command = ["python", sync_script, selected_sumocfg, "--sumo-gui", "--sync-vehicle-color"]
                subprocess.Popen(sync_command, cwd=os.path.dirname(sync_script))

                if spectate_var.get():
                    try:
                        print("Starting spectator")
                        spectatorpath = "./spectator.py"
                        spectatordir = os.path.dirname(spectatorpath)
                        subprocess.Popen(["python", spectatorpath, spectatordir])
                        print("Spectator started")
                    except FileNotFoundError as e:
                        print("Couldn't start the spectator: ", e)

                run_simulation(selected_map)

            except FileNotFoundError as e:
                print("Couldn't start the simulation: ", e)

        else:
            # SUMO only
            start_sumo(selected_sumocfg)
            run_simulation(selected_map)

def hudSelection():
    """
    Gather user selections from string_hud_frames,
    convert brightness/fov to numeric values, run calculations,
    then return the hud_data dictionary.
    """
    for hud in string_hud_frames:
        brightness_str = hud['brightness_var']
        frequency_str = hud['frequency_var']
        relevance_str = hud['relevance_var']
        fov_str = hud['fov_var']
        vehicle_type = hud['vehicle_type']
        HUDname = hud['HUDname']

        # Convert string back to float
        try:
            brightness_val = float(brightness_str)
        except ValueError:
            brightness_val = 0.4

        try:
            fov_val = float(fov_str)
        except ValueError:
            fov_val = 60.0

        # Now call calculations with numeric brightness, fov
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
            'reactTime':         reactTime,
            'fatigueness_level': fatigueness_level,
            'awareness_level':   awareness_level,
            'max_speed':         maxSpeed,
            "min_Gap":           minGap,
            'vehicle_type':      vehicle_type,
            'speed_factor':      speedFactor,
            'accel_factor':      accel,
            'brightness':        brightness_val,  
            'frequency':         frequency_str,
            'relevance':         relevance_str,
            'field of view':     fov_val         
        }
    return hud_data

def writeXML(hud_list):
    """
    Writes HUD data to an XML (hudconfig.xml) for the spectator client, 
    storing the user-chosen strings. You could also store numeric values if you prefer.
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
    pretty_xml_as_string = dom.toprettyxml()
    with open(xml_file_path, "w") as f:
        f.write(pretty_xml_as_string)

    return xml_file_path

def update_vehicles(xml_file_path, hud_data):
    """
    Function that updates the vehicle types in the .rou.xml file 
    with new behaviors (maxSpeed, speedFactor, etc.)
    """
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    for vehicle_type, data in hud_data.items():
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

                color = "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                vtype_elem.set('color', color)

    tree.write(xml_file_path, encoding='utf-8', xml_declaration=True)

def prettify(elem):
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")

def start_sumo(selected_sumocfg):
    try:
        subprocess.Popen(['sumo-gui', '-c', selected_sumocfg])
    except FileNotFoundError:
        print("Couldn't start SUMO. Please check if your SUMO path is correct.")

def modify_vehicle_routes(selected_map):
    """
    Function to set the vehicle types in the .rou file according 
    to user probabilities.
    """
    original_routes_file = os.path.join(sumo_base_dir, "examples", "rou", selected_map + ".rou.xml")

    try:
        tree = ET.parse(original_routes_file)
        root = tree.getroot()

        vehicle_types = []
        probabilities = []

        for hud in string_hud_frames:
            probability = int(hud['entry'])
            vehicle_type = hud['vehicle_type']
            vehicle_types.append(vehicle_type)
            probabilities.append(probability)

        for vehicle in root.findall('vehicle'):
            if vehicle_types:
                vehicle_id = vehicle.get('id')
                # Randomly pick a vehicle type based on the given probability
                chosen_vehicle_type = random.choices(vehicle_types, probabilities)[0]
                vehicle.set('type', chosen_vehicle_type)
                vehicle_type_mapping[vehicle_id] = chosen_vehicle_type

        tree.write(original_routes_file)

    except FileNotFoundError:
        print(f"Couldn't find: {original_routes_file}")

def close_window():
    root.destroy()

next_hud_id = 1

def add_hud():
    global next_hud_id
    if len(hud_frames) >= len(all_vehicle_types):
        messagebox.showwarning("No available IDs", "There are no vehicle types available for simulation!")
        return

    hud_frame = create_hud_frame(next_hud_id)
    hud_frames.append(hud_frame)

    vehicle_type = hud_frame['vehicle_type'].get()
    available_vehicle_types.remove(vehicle_type)

    hud_frame['frame'].pack(pady=10, padx=20, ipadx=10, ipady=10, fill="x")
    update_scrollregion()
    
    print("Added HUD: " + str(len(hud_frames)))
    next_hud_id += 1

def remove_hud(hud_id):
    global hud_frames
    hud_to_remove = next((hud for hud in hud_frames if hud['hud_id'] == hud_id), None)
    if hud_to_remove:
        vehicle_type = hud_to_remove['vehicle_type'].get()
        available_vehicle_types.append(vehicle_type)
        hud_to_remove['frame'].destroy()
        hud_frames = [hud for hud in hud_frames if hud['hud_id'] != hud_id]
        update_scrollregion()
    else:
        print(f"No HUD found with ID: {hud_id}")

def update_scrollregion():
    canvas.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

def validate_integer_input(value):
    return value.isdigit() and int(value) > 0

def on_validate_input(value, entry):
    reselect_map()
    if validate_integer_input(value):
        entry.config(bg="white")
    else:
        entry.config(bg="red")
    return True

def create_hud_frame(next_hud_id):
    """
    Create the frame for a new HUD, with user-selectable 
    brightness/fov *sliders*.
    """
    hud_number = len(hud_frames) + 1

    frame = tk.Frame(scrollable_frame, bg="white", bd=2, relief="raised")

    global header_entry
    header_entry = tk.Entry(frame, width=20, font=('Helvetica', 14, 'bold'))
    header_entry.insert(0, f"HUD {hud_number}")
    header_entry.grid(row=0, column=0, pady=10, padx=10, sticky='n')

    label_prob = tk.Label(frame, text="HUD Probability: ", bg="white", font=('Helvetica', 11))
    label_prob.grid(row=1, column=0, pady=5, padx=10, sticky='w')
    
    probability_var = tk.StringVar()
    probability_entry = tk.Entry(frame, textvariable=probability_var, width=15, font=('Helvetica', 11))

    validate_command = frame.register(lambda val: on_validate_input(val, probability_entry))
    probability_entry.config(validate="key", validatecommand=(validate_command, "%P"))
    probability_entry.insert(0, "1")
    probability_entry.grid(row=1, column=1, pady=5, padx=10, sticky='w')

    # ---------- BRIGHTNESS SLIDER ----------
    label_brightness = tk.Label(frame, text="HUD brightness: ", bg="white", font=('Helvetica', 11))
    label_brightness.grid(row=2, column=0, pady=5, padx=10, sticky='w')

    # This slider goes from 0.0 to 0.9 in increments of 0.01
    brightness_scale = tk.Scale(
        frame,
        from_=0.0,
        to=0.9,
        resolution=0.01,
        orient=tk.HORIZONTAL,
        length=150,
        bg="white",
        font=('Helvetica', 10),
        tickinterval=0.3
    )
    brightness_scale.set(0.4)  # default
    brightness_scale.grid(row=2, column=1, pady=5, padx=10, sticky='ew')

    # ---------- FREQUENCY DROPDOWN ----------
    label_frequency = tk.Label(frame, text="Information frequency: ", bg="white", font=('Helvetica', 11))
    label_frequency.grid(row=3, column=0, pady=5, padx=10, sticky='w')
    
    frequency_var = tk.StringVar(frame)
    frequency_var.set(information_frequency[1])  # "average"
    frequency_menu = ttk.Combobox(
        frame, 
        textvariable=frequency_var, 
        values=information_frequency, 
        state="readonly", 
        font=('Helvetica', 11)
    )
    frequency_menu.current(1)
    frequency_menu.grid(row=3, column=1, pady=5, padx=10, sticky='ew')

    label_relevance = tk.Label(frame, text="Information relevance: ", bg="white", font=('Helvetica', 11))
    label_relevance.grid(row=4, column=0, pady=5, padx=10, sticky='w')
    
    relevance_var = tk.StringVar(frame)
    relevance_var.set(information_relevance[1])  # "neutral"
    relevance_menu = ttk.Combobox(
        frame, 
        textvariable=relevance_var, 
        values=information_relevance, 
        state="readonly", 
        font=('Helvetica', 11)
    )
    relevance_menu.current(1)
    relevance_menu.grid(row=4, column=1, pady=5, padx=10, sticky='ew')

    # ---------- FOV SLIDER ----------
    label_fov = tk.Label(frame, text="Field of View: ", bg="white", font=('Helvetica', 11))
    label_fov.grid(row=5, column=0, pady=5, padx=10, sticky='w')

    # Slider range 30..100 degrees
    fov_scale = tk.Scale(
        frame,
        from_=30,
        to=100,
        resolution=1,
        orient=tk.HORIZONTAL,
        length=150,
        bg="white",
        font=('Helvetica', 10),
        tickinterval=20
    )
    fov_scale.set(60)  # default
    fov_scale.grid(row=5, column=1, pady=5, padx=10, sticky='ew')

    label_vehicle_type = tk.Label(frame, text="Select vehicle type:", bg="white", font=('Helvetica', 11))
    label_vehicle_type.grid(row=6, column=0, pady=5, padx=10, sticky='w')

    max_width = max(len(option) for option in available_vehicle_types) + 2
    vehicle_type = tk.StringVar(frame)
    vehicle_type_menu = ttk.Combobox(frame, textvariable=vehicle_type, values=available_vehicle_types, state="readonly", font=('Helvetica', 11))
    vehicle_type_menu.current(0)
    vehicle_type_menu.config(width=max_width)
    vehicle_type_menu.grid(row=6, column=1, pady=5, padx=10, sticky='ew')
    
    # Now we'll store references so we can retrieve slider values
    hud = {
        'frame':         frame,
        'HUDname':       header_entry,
        'entry':         probability_entry,

        # We store the actual slider widgets (not strings) 
        # so we can get numeric values from them directly
        'brightness_var': brightness_scale,
        'frequency_var':  frequency_var,
        'relevance_var':  relevance_var,
        'fov_var':        fov_scale,

        'vehicle_type':   vehicle_type,
        'hud_id':         next_hud_id
    }

    remove_button = tk.Button(
        frame, 
        text="Remove HUD", 
        command=lambda: remove_hud(hud.get("hud_id")), 
        bg="#ff6347", 
        fg="white", 
        width=15, 
        font=('Helvetica', 12)
    )
    remove_button.grid(row=7, column=0, columnspan=2, pady=10)

    return hud

def close_window():
    root.quit()

selected_map_index = None
def on_map_select(event):
    global selected_map_index
    selected_index = map_list.curselection()
    if selected_index:
        selected_map_index = selected_index[0]

def reselect_map():
    if selected_map_index is not None:
        map_list.selection_clear(0, tk.END)
        map_list.selection_set(selected_map_index)
        map_list.activate(selected_map_index)

root = tk.Tk()
root.title("SUMO Simulation Launcher")

window_width = 800
window_height = 800
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x_coordinate = (screen_width - window_width) // 2
y_coordinate = (screen_height - window_height) // 2
root.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill="both")

main_tab = ttk.Frame(notebook)
notebook.add(main_tab, text="Main")

# SETTINGS PAGE
settings_tab = ttk.Frame(notebook)
notebook.add(settings_tab, text="Settings")

canvas = tk.Canvas(settings_tab)
scrollbar = ttk.Scrollbar(settings_tab, orient="vertical", command=canvas.yview)
scrollable_frame = ttk.Frame(canvas)

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

def on_mouse_wheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

canvas.bind("<MouseWheel>", on_mouse_wheel)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

header_label = tk.Label(
    scrollable_frame, 
    text=(
        "This is the settings page. Here you can enable and disable which data "
        "will be saved into the .csv during the simulation. By default, all "
        "options are enabled."
    ),
    font=("Arial", 12),
    bg="white"
)
header_label.grid(row=0, column=0, columnspan=2, padx=80, pady=5, sticky="we")

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

checkbox_vars = []
for i, text in enumerate(checkbox_texts):
    label = ttk.Label(scrollable_frame, text=text, background="white")
    label.grid(row=i + 1, column=0, padx=10, pady=5, sticky="e")
    checkbox_var = tk.BooleanVar(value=True)
    checkbox = ttk.Checkbutton(scrollable_frame, variable=checkbox_var)
    checkbox.grid(row=i + 1, column=1, pady=5, sticky="w")
    checkbox_vars.append(checkbox_var)

scrollable_frame.update_idletasks()
canvas.configure(scrollregion=canvas.bbox("all"))

# HELP PAGE
help_tab = ttk.Frame(notebook)
notebook.add(help_tab, text="Help")
# (Omitted for brevity.)

simulate_var = tk.BooleanVar()
simulate_var.set(False)
spectate_var = tk.BooleanVar()
spectate_var.set(False)
hudless_var = tk.BooleanVar()
hudless_var.set(False)

map_label = tk.Label(main_tab, text="Select a map:", font=('Helvetica', 14, 'bold'))
map_label.pack(pady=5)

map_list = tk.Listbox(main_tab, font=('Helvetica', 12), height=5, width=10)
for map_name in maps:
    map_list.insert(tk.END, map_name)
map_list.pack(pady=10)
map_list.bind('<<ListboxSelect>>', on_map_select)

simulate_checkbox = tk.Checkbutton(main_tab, text="Start co-Simulation with CARLA", variable=simulate_var, font=('Helvetica', 12))
simulate_checkbox.pack()

spectator_checkbox = tk.Checkbutton(main_tab, text="Start the CARLA first-person spectator client", variable=spectate_var, font=('Helvetica', 12))
spectator_checkbox.pack()

hudless_checkbox = tk.Checkbutton(
    main_tab, 
    text="Simulate a car without a HUD.\nProbability for the HUD is always 5.", 
    variable=hudless_var, 
    font=('Helvetica', 12)
)
hudless_checkbox.pack()

canvas = tk.Canvas(main_tab, bg="#f0f0f0")
scrollbar = tk.Scrollbar(main_tab, orient="vertical", command=canvas.yview)
scrollable_frame = tk.Frame(canvas, bg="#f0f0f0")

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)
canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

hud_frames = []

def create_default_huds():
    for _ in range(3):
        add_hud()

button_frame = tk.Frame(main_tab, bg="#f0f0f0")
button_frame.pack(pady=10)

button_width = 20
button_height = 2

add_hud_button = tk.Button(button_frame, text="Add HUD", command=add_hud, bg="#4682b4", fg="white", width=button_width, height=button_height, font=('Helvetica', 10))
add_hud_button.pack(pady=10)

start_button = tk.Button(button_frame, text="Start simulation", command=start_simulation, bg="#32cd32", fg="white", width=button_width, height=button_height, font=('Helvetica', 10))
start_button.pack(pady=10)

close_button = tk.Button(button_frame, text="Close", command=close_window, bg="#a9a9a9", fg="white", width=button_width, height=button_height, font=('Helvetica', 10))
close_button.pack(pady=10, padx=10)

scrollable_frame.unbind_class("TCombobox", "<MouseWheel>")

def dontscroll(e):
    return "dontscroll"

def on_enter(e):
    scrollable_frame.bind_all("<MouseWheel>", dontscroll)

def _on_mouse_wheel(event):
    canvas.yview_scroll(-1 * int((event.delta / 120)), "units")

def on_leave(e):
    scrollable_frame.bind_all("<MouseWheel>", _on_mouse_wheel)

scrollable_frame.bind_class('Listbox', '<Enter>', on_enter)
scrollable_frame.bind_class('Listbox', '<Leave>', on_leave)

create_default_huds()
root.mainloop()
