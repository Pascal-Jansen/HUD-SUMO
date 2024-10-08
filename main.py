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

brightness_level = ["very dark", "dark", "average", "bright", "very bright"]
information_frequency = ["minimum", "average", "maximum"]
information_relevance = ["unimportant", "neutral", "important"]
fov = ["small", "medium", "large"]

hud_count = 0

vehicle_type_mapping = {}

hud_data = {}

available_vehicle_types = [
    "vehicle.audi.a2", "vehicle.audi.tt",
    "vehicle.chevrolet.impala", "vehicle.mini.cooper_s", "vehicle.mercedes.coupe",
    "vehicle.bmw.grandtourer", "vehicle.citroen.c3", "vehicle.ford.mustang",
    "vehicle.volkswagen.t2", "vehicle.lincoln.mkz_2017", "vehicle.seat.leon"
]

all_vehicle_types = [
    "vehicle.audi.a2", "vehicle.audi.tt",
    "vehicle.chevrolet.impala", "vehicle.mini.cooper_s", "vehicle.mercedes.coupe",
    "vehicle.bmw.grandtourer", "vehicle.citroen.c3", "vehicle.ford.mustang",
    "vehicle.volkswagen.t2", "vehicle.lincoln.mkz_2017", "vehicle.seat.leon"
]

vtypes_xml_path = carla_base_dir+r"\Co-Simulation\Sumo\examples\carlavtypes.rou.xml"

base_frame = {
        'HUDname': "HUD-less car",
        'entry': 5,
        'brightness_var': "none",
        'frequency_var': "none",
        'relevance_var': "none",
        'fov_var': "none",
        'vehicle_type': "vehicle.nissan.patrol",
        'hud_id': "999" 
    }

hud_id_mapping = {}

objects=[]

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


"""
Function that handles getting the data from the simulation via Traci and setting the 
minimal Gap dynamically. 
"""
def run_simulation(map):

    min_gap_mapping = {}

    for vehicle_type, data in hud_data.items():
        min_gap = data.get("min_Gap")  
        min_gap_mapping[vehicle_type] = min_gap
    
    path = os.path.join(sumo_base_dir, "examples", map + ".sumocfg")
    traci.start(["sumo", "-c", path])
    
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

            simulation_data.append([vehicle_id, simTime, position[0], position[1], current_speed, current_gap, current_acceleration, distance_traveled, time_loss])
            
            vehicle_type = vehicle_type_mapping.get(vehicle_id, "unknown")

            min_gap_for_vehicle_type = hud_data.get(vehicle_type, {}).get("min_Gap", 1)

            new_min_gap = max(2.0, (current_speed * 0.5 * min_gap_for_vehicle_type))

            traci.vehicle.setMinGap(vehicle_id, new_min_gap)
    

    traci.close()

    save_simulation_data(simulation_data, map)


"""
Function that checks which boxes on the setting tab are checked. If a box is checked
this function takes the collected data from Traci or the saved data from the HUD
settings and stores it in the .csv
"""
def save_simulation_data(simulation_data, map):

    if not simulation_data or not isinstance(simulation_data, list):
        print("No simulation data available!")
        return
    
    if not any(var.get() for var in checkbox_vars ):
        print("No simulation data will be saved!")
        return
    
    fieldnames = []
    
    if checkbox_vars[0].get():  # Map Name
        fieldnames.append('map')
    if checkbox_vars[1].get():  # Vehicle ID
        fieldnames.append('vehicle_id')
    if checkbox_vars[2].get():  # HUD ID
        fieldnames.append('hud_id')
    if checkbox_vars[3].get():  # Simulation Step
        fieldnames.append('simulation_time')
    if checkbox_vars[4].get():  # Vehicle Type
        fieldnames.append('vehicle_type')
    if checkbox_vars[5].get():  # Position X
        fieldnames.append('position_x')
    if checkbox_vars[6].get():  # Position Y
        fieldnames.append('position_y')
    if checkbox_vars[7].get():  # Current Speed
        fieldnames.append('current_speed')
    if checkbox_vars[8].get():  # Current Gap
        fieldnames.append('current_gap')
    if checkbox_vars[9].get():  # Current Acceleration
        fieldnames.append('current_acceleration')
    if checkbox_vars[10].get():  # Distance Traveled
        fieldnames.append('distance_traveled')
    if checkbox_vars[11].get():  # Time Loss
        fieldnames.append('time_loss')
    if checkbox_vars[12].get():  # Max Speed
        fieldnames.append('maxSpeed')
    if checkbox_vars[13].get():  # Speed Adherence Factor
        fieldnames.append('speedAdherenceFactor')
    if checkbox_vars[14].get():  # Reaction Time
        fieldnames.append('reactionTime')
    if checkbox_vars[15].get():  # Fatigueness Level
        fieldnames.append('fatiguenessLevel')
    if checkbox_vars[16].get():  # Awareness Level
        fieldnames.append('awarenessLevel')
    if checkbox_vars[17].get():  # Accel Factor
        fieldnames.append('acceleration')
    if checkbox_vars[18].get():  # Min Gap Factor
        fieldnames.append('minGapFactor')
    if checkbox_vars[19].get():  # Distraction Level
        fieldnames.append('distractionLevel')
    if checkbox_vars[20].get():  # Brightness
        fieldnames.append('brightness')
    if checkbox_vars[21].get():  # Information Frequency
        fieldnames.append('information_frequency')
    if checkbox_vars[22].get():  # Information Relevance
        fieldnames.append('information_relevance')
    if checkbox_vars[23].get():  # FoV
        fieldnames.append('FoV')
    
    
    now = datetime.now()

    timestamp = now.strftime("%H-%M-%S_%Y-%m-%d")

    csv_filename = f'Simulation_data/{map}_{timestamp}_simulation_data.csv'    

    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for entry in simulation_data:

            row_data = {}

            vehicle_type = vehicle_type_mapping.get(entry[0], "unknown")

            hud_data_for_type = hud_data.get(vehicle_type, {})

            hud_name = hud_data_for_type.get('HUDname', 'N/A')

            hud_id = hud_id_mapping.get(vehicle_type, "unknown")

            idName = f"{hud_id}_{hud_name}"


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
                row_data['maxSpeed'] = max_speed = hud_data_for_type.get('max_speed', 'N/A')
            if checkbox_vars[13].get(): 
                row_data['speedAdherenceFactor'] = speedFactor = hud_data_for_type.get('speed_factor', 'N/A')
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

"""
Function to make sure all saved huds only hold string values.
"""
def convert_hudFrames():

    for hud in hud_frames:
        string_hud = {
            'HUDname': str(hud['HUDname'].get()),
            'entry': str(hud['entry'].get()),
            'brightness_var': str(hud['brightness_var'].get()),
            'frequency_var': str(hud['frequency_var'].get()),
            'relevance_var': str(hud['relevance_var'].get()),
            'fov_var': str(hud['fov_var'].get()),
            'vehicle_type': str(hud['vehicle_type'].get()),
            'hud_id': str(hud['hud_id'])
        }
    
        string_hud_frames.append(string_hud)

    print(string_hud_frames)

def map_vehicle_type_to_hud_id():
    for hud in string_hud_frames:
        vehicle_type = hud['vehicle_type']  
        hud_id = hud['hud_id'] 
        
        hud_id_mapping[vehicle_type] = hud_id


"""
Function that handles the start of the simulation. First it checks if all fields are valid.
Then it checks the simulation settings: simulation with CARLA server/ first person client 
or with an HUD-less car.

Increase sleep timer if CARLA takes longer to start.
"""
def start_simulation():
    if not map_list.curselection():
        messagebox.showwarning("No map selected", "Please select a map for the simulation.")
        return
    
    if not are_all_fields_valid():
        messagebox.showwarning("Invalid Inputs", "Please enter valid inputs for all the input fields!")
        return
    
    if hudless_var.get() == False and len(hud_frames) == 0:
        messagebox.showwarning("No simulation data", "Please allow simulation without HUD or create HUDs to simulate.")
        return

    selected_index = map_list.curselection()

    global hud_count

    convert_hudFrames()

    if hudless_var.get():
        string_hud_frames.append(base_frame)
        hud_id_mapping["vehicle.nissan.patrol"] = "999"

    map_vehicle_type_to_hud_id()

    hud_data = hudSelection()

    update_vehicles(carla_base_dir + r"\Co-Simulation\Sumo\examples\carlavtypes.rou.xml", hud_data)

    if selected_index:
        selected_map = map_list.get(selected_index[0])
        selected_sumocfg = maps[selected_map]

        writeXML(string_hud_frames)

        modify_vehicle_routes(selected_map)

        carla_exe = os.path.join(carla_base_dir, "CarlaUE4.exe")

        if spectate_var.get() and simulate_var.get() == False:

            try: 
                print("Starting CARLA in RenderOffScreenMode")
                subprocess.Popen([carla_exe, "-RenderOffScreen"])

                time.sleep(20)
                print("Wating time after the start of CARLA...")

                print("Starting configuration script: {}".format(config_script))
                config_command = ["python", config_script, "--map", selected_map]
                configsubprocess = subprocess.Popen(config_command, cwd=os.path.dirname(config_script))
                configsubprocess.wait()

                sync_script = os.path.join(sumo_base_dir, "run_synchronization.py")
                print("Starting synchronisation script with SUMO: {}".format(selected_sumocfg))
                sync_command = ["python", sync_script, selected_sumocfg, "--sumo-gui", "--sync-vehicle-color"]
                subprocess.Popen(sync_command, cwd=os.path.dirname(sync_script))
                
                try:
                    print("starting spectator")
                    spectatorpath = "./spectator.py"
                    spectatordir = os.path.dirname(spectatorpath)
                    subprocess.Popen(["python", spectatorpath, spectatordir])
                    print("started spectator")
                except FileNotFoundError as e:
                    print("Couldn't start the spectator", e)

                run_simulation(selected_map)

            except FileNotFoundError as e:
                print("Couldn't start the simulation:", e)

        elif simulate_var.get():
            carla_exe = os.path.join(carla_base_dir, "CarlaUE4.exe")

            try:
                print("Starting CarlaUE4.exe...")
                subprocess.Popen([carla_exe])

                time.sleep(20)
                print("Wating time after the start of CARLA...")

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
                        print("starting spectator")
                        spectatorpath = "./spectator.py"
                        spectatordir = os.path.dirname(spectatorpath)
                        subprocess.Popen(["python", spectatorpath, spectatordir])
                        print("started spectator")
                    except FileNotFoundError as e:
                        print("Couldn't start the spectator: ", e)

                run_simulation(selected_map)

            except FileNotFoundError as e:
                print("Couldn't start the simulation: ", e)

        else:
            start_sumo(selected_sumocfg)
            run_simulation(selected_map)


"""
Function that saves the selected options and the calculated data
"""
def hudSelection():

    for hud in string_hud_frames:
        brightness_level = hud['brightness_var']
        information_frequency = hud['frequency_var']
        information_relevance = hud['relevance_var']
        fov_selection = hud['fov_var']
        vehicle_type = hud['vehicle_type']
        HUDname = hud['HUDname']

        distraction_level = calculations.calc_distraction(information_relevance, information_frequency, brightness_level, fov_selection)
        fatigueness_level = calculations.calc_fatigueness(information_relevance, information_frequency, brightness_level)
        awareness_level = calculations.calc_awareness(information_relevance, information_frequency, distraction_level, fatigueness_level, fov_selection)
        reactTime = calculations.calc_ReactTime(distraction_level, fatigueness_level, awareness_level)
        maxSpeed = calculations.calc_MaxSpeed(awareness_level, fatigueness_level, distraction_level, information_frequency)
        minGap= calculations.calc_MinGap(distraction_level, fatigueness_level, awareness_level, fov_selection)
        speedFactor = calculations.calc_SpeedAd(fov_selection, distraction_level, fatigueness_level, awareness_level, information_relevance, information_frequency)
        accel = calculations.calc_acceleration(fatigueness_level, distraction_level, awareness_level, information_relevance)

        hud_data[vehicle_type] = {
            'HUDname': HUDname,
            'distraction_level': distraction_level,
            'reactTime': reactTime,
            'fatigueness_level': fatigueness_level,
            'awareness_level': awareness_level,
            'max_speed': maxSpeed,
            "min_Gap": minGap,
            'vehicle_type': vehicle_type,
            'speed_factor': speedFactor,
            'accel_factor': accel,
            'brightness': brightness_level,
            'frequency': information_frequency,
            'relevance': information_relevance,
            'field of view': fov_selection
        }

    return hud_data


"""
Function that writes the .xml file for the spectator client.
It saves the settings of every HUD so that they can be easily accessed.
"""
def writeXML(hud_list):
    root = ET.Element("Vehicles")
  
    for hud in hud_list:
        vehicle_type = hud['vehicle_type']
        brightness = hud['brightness_var']
        frequency = hud['frequency_var']
        relevance = hud['relevance_var']
        fov = hud['fov_var']
        hud_name = hud['HUDname']

        vehicle_element = ET.SubElement(root, "Vehicle", type_id=vehicle_type)
        ET.SubElement(vehicle_element, "HUDName").text = hud_name
        ET.SubElement(vehicle_element, "Brightness").text = brightness
        ET.SubElement(vehicle_element, "Frequency").text = frequency
        ET.SubElement(vehicle_element, "Relevance").text = relevance
        ET.SubElement(vehicle_element, "FoV").text = fov

    tree = ET.ElementTree(root)
    xml_file_path = "hudconfig.xml"
    tree.write(xml_file_path, encoding="utf-8", xml_declaration=True)

    dom = minidom.parseString(ET.tostring(root))
    pretty_xml_as_string = dom.toprettyxml()
    with open(xml_file_path, "w") as f:
        f.write(pretty_xml_as_string)

    return xml_file_path


"""
Function that updates the vehicle types in the .rou.xml file.
This update is important to set new behaviour to the cars that are being simulated.
"""
def update_vehicles(xml_file_path, hud_data):
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    for vehicle_type, data in hud_data.items():

        if vehicle_type.lower() == "vehicle.nissan.patrol":
            continue

        max_speed = data['max_speed']
        speedFactor = data.get('speed_factor', '')
        reactionTime = data.get('reactTime')
        accelFactor = data.get('accel_factor')

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


"""
Function to set the vehicle types in the .rou file. 
"""
def modify_vehicle_routes(selected_map):
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

                vehicle_type = random.choices(vehicle_types, probabilities)[0]  

                vehicle.set('type', vehicle_type)

                vehicle_type_mapping[vehicle_id] = vehicle_type

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


def on_selection(event):
    dropdown = event.widget
    selected_value = dropdown.get()

    for i, (label, combobox, previous_value) in enumerate(objects):
        if combobox == dropdown:
            if previous_value not in available_vehicle_types:
                available_vehicle_types.append(previous_value)
                
            if selected_value in available_vehicle_types:
                available_vehicle_types.remove(selected_value)

            objects[i] = (label, combobox, selected_value)
            break

    update_comboboxes()

    reselect_map() 

def update_comboboxes():
    for _, dropdown, _ in objects:
        if dropdown.winfo_exists():  
            dropdown['values'] = available_vehicle_types

def validate_integer_input(value):
    return value.isdigit() and int(value) > 0

def on_validate_input(value, entry):
    reselect_map() 
    if validate_integer_input(value):
        entry.config(bg="white") 
    else:
        entry.config(bg="red")  
    return True  


"""
Function for the HUD frames that makes it possible for the user to create
new AR HUDs
"""
def create_hud_frame(next_hud_id):
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

    validate_command = frame.register(lambda value: on_validate_input(value, probability_entry))
    probability_entry.config(validate="key", validatecommand=(validate_command, "%P"))
    probability_entry.insert(0, "1") 
    probability_entry.grid(row=1, column=1, pady=5, padx=10, sticky='w')

    prob_tooltip = ToolTip(probability_entry, "Probability is set in fractions. Please only use integers > 0.")

    prob_question_button = tk.Button(frame, text="?", command=prob_tooltip.show_tooltip, width=3)
    prob_question_button.grid(row=1, column=2, padx=5)
    prob_question_button.bind("<Enter>", lambda event, tooltip=prob_tooltip: tooltip.show_tooltip())
    prob_question_button.bind("<Leave>", lambda event, tooltip=prob_tooltip: tooltip.hide_tooltip())

    label_brightness = tk.Label(frame, text="HUD brightness: ", bg="white", font=('Helvetica', 11))
    label_brightness.grid(row=2, column=0, pady=5, padx=10, sticky='w')
    
    brightness_var = tk.StringVar(frame)
    brightness_var.set(brightness_level[2])
    brightness_menu = ttk.Combobox(frame, textvariable=brightness_var, values=brightness_level, state="readonly", font=('Helvetica', 11))
    brightness_menu.current(1)
    brightness_menu.grid(row=2, column=1, pady=5, padx=10, sticky='ew')

    brightness_menu.bind('<<ComboboxSelected>>', on_selection)

    brightness_tooltip = ToolTip(brightness_menu, "Very dark: HUD is very visible.\nVery bright: HUD is almost see-through.")
    
    brightness_question_button = tk.Button(frame, text="?", command=brightness_tooltip.show_tooltip, width=3)
    brightness_question_button.grid(row=2, column=2, padx=5)
    brightness_question_button.bind("<Enter>", lambda event, tooltip=brightness_tooltip: tooltip.show_tooltip())
    brightness_question_button.bind("<Leave>", lambda event, tooltip=brightness_tooltip: tooltip.hide_tooltip())

    label_frequency = tk.Label(frame, text="Information frequency: ", bg="white", font=('Helvetica', 11))
    label_frequency.grid(row=3, column=0, pady=5, padx=10, sticky='w')
    
    frequency_var = tk.StringVar(frame)
    frequency_var.set(information_frequency[1])
    frequency_menu = ttk.Combobox(frame, textvariable=frequency_var, values=information_frequency, state="readonly", font=('Helvetica', 11))
    frequency_menu.current(1) 
    frequency_menu.grid(row=3, column=1, pady=5, padx=10, sticky='ew')

    frequency_menu.bind('<<ComboboxSelected>>', on_selection)

    frequency_tooltip = ToolTip(frequency_menu, "Minimum: the information is only displayed when needed\nMaximum: information is always displayed")
    
    frequency_question_button = tk.Button(frame, text="?", command=frequency_tooltip.show_tooltip, width=3)
    frequency_question_button.grid(row=3, column=2, padx=5)
    frequency_question_button.bind("<Enter>", lambda event, tooltip=frequency_tooltip: tooltip.show_tooltip())
    frequency_question_button.bind("<Leave>", lambda event, tooltip=frequency_tooltip: tooltip.hide_tooltip())

    label_relevance = tk.Label(frame, text="Information relevance: ", bg="white", font=('Helvetica', 11))
    label_relevance.grid(row=4, column=0, pady=5, padx=10, sticky='w')
    
    relevance_var = tk.StringVar(frame)
    relevance_var.set(information_relevance[1])
    relevance_menu = ttk.Combobox(frame, textvariable=relevance_var, values=information_relevance, state="readonly", font=('Helvetica', 11))
    relevance_menu.current(1) 
    relevance_menu.grid(row=4, column=1, pady=5, padx=10, sticky='ew')

    relevance_menu.bind('<<ComboboxSelected>>', on_selection)

    relevance_tooltip = ToolTip(relevance_menu, "Unimportant: HUD presents important information and information about your media, the weather,...\nImportant: HUD presents only information that is needed like current speed and navigation instructions.")
    
    relevance_question_button = tk.Button(frame, text="?", command=relevance_tooltip.show_tooltip, width=3)
    relevance_question_button.grid(row=4, column=2, padx=5)
    relevance_question_button.bind("<Enter>", lambda event, tooltip=relevance_tooltip: tooltip.show_tooltip())
    relevance_question_button.bind("<Leave>", lambda event, tooltip=relevance_tooltip: tooltip.hide_tooltip())

    label_fov = tk.Label(frame, text="Field of View: ", bg="white", font=('Helvetica', 11))
    label_fov.grid(row=5, column=0, pady=5, padx=10, sticky='w')
    
    fov_var = tk.StringVar(frame)
    fov_var.set(fov[1])
    fov_menu = ttk.Combobox(frame, textvariable=fov_var, values=fov, state="readonly", font=('Helvetica', 11))
    fov_menu.current(1)
    fov_menu.grid(row=5, column=1, pady=5, padx=10, sticky='ew')

    fov_menu.bind('<<ComboboxSelected>>', on_selection)

    fov_tooltip = ToolTip(fov_menu, "Small: Information is displayed directly above steering wheel.\nLarge: Information is displayed on whole windshield.")
    
    fov_question_button = tk.Button(frame, text="?", command=fov_tooltip.show_tooltip, width=3)
    fov_question_button.grid(row=5, column=2, padx=5)
    fov_question_button.bind("<Enter>", lambda event, tooltip=fov_tooltip: tooltip.show_tooltip())
    fov_question_button.bind("<Leave>", lambda event, tooltip=fov_tooltip: tooltip.hide_tooltip())

    label_vehicle_type = tk.Label(frame, text="Select vehicle type:", bg="white", font=('Helvetica', 11))
    label_vehicle_type.grid(row=6, column=0, pady=5, padx=10, sticky='w')

    max_width = max(len(option) for option in available_vehicle_types) + 2  
    vehicle_type = tk.StringVar(frame)
    vehicle_type_menu = ttk.Combobox(frame, textvariable=vehicle_type, values=available_vehicle_types, state="readonly", font=('Helvetica', 11))
    vehicle_type_menu.current(0)  
    vehicle_type_menu.config(width=max_width) 
    vehicle_type_menu.grid(row=6, column=1, pady=5, padx=10, sticky='ew')

    vehicle_type_menu.bind('<<ComboboxSelected>>', on_selection)
    
    objects.append((label_vehicle_type, vehicle_type_menu, vehicle_type.get()))

    hud = {
        'frame': frame,
        'HUDname': header_entry,
        'entry': probability_entry,
        'brightness_var': brightness_var,
        'frequency_var': frequency_var,
        'relevance_var': relevance_var,
        'fov_var': fov_var,
        'vehicle_type': vehicle_type,
        'hud_id': next_hud_id 
    }

    remove_button = tk.Button(frame, text="Remove HUD", command=lambda: remove_hud(hud.get("hud_id")), bg="#ff6347", fg="white", width=15, font=('Helvetica', 12))
    remove_button.grid(row=7, column=0, columnspan=3, pady=10)

    return hud

def dropdown_opened(dropdown):
    dropdown['values'] = available_vehicle_types 

def getList():
    return available_vehicle_types

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 250
        y += self.widget.winfo_rooty() + 20

        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(self.tooltip_window, text=self.text, justify='left',
                         background='#ffffe0', relief='solid', borderwidth=1,
                         wraplength=200)
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def update_scrollregion():
    canvas.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

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


#°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°#
#--------------------SETTINGS PAGE--------------------#
#°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°#


# Scrollable frame setup
settings_tab = ttk.Frame(notebook)
notebook.add(settings_tab, text="Settings")

# Create a Canvas to allow scrolling
canvas = tk.Canvas(settings_tab)
scrollbar = ttk.Scrollbar(settings_tab, orient="vertical", command=canvas.yview)
scrollable_frame = ttk.Frame(canvas)

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(
        scrollregion=canvas.bbox("all")
    )
)

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

def on_mouse_wheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

canvas.bind("<MouseWheel>", on_mouse_wheel)


# Layout the canvas and scrollbar
canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# Header Label
header_label = tk.Label(scrollable_frame, text="This is the settings page. Here you can enable and disable which data will be saved into the \n .csv during the simulation."
                                               "By default all the options are enabled.", font=("Arial", 12))
header_label.grid(row=0, column=0, columnspan=2, padx=80, pady=5, sticky="we")  # Center the header
 

# Individuelle Texte für jede Checkbox
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

# Create 20 labels and checkboxes with unique text
checkbox_vars = []
for i, text in enumerate(checkbox_texts):
    label = ttk.Label(scrollable_frame, text=text)
    label.grid(row=i + 1, column=0, padx=10, pady=5, sticky="e")
    
    checkbox_var = tk.BooleanVar(value="true")
    checkbox = ttk.Checkbutton(scrollable_frame, variable=checkbox_var)
    checkbox.grid(row=i + 1, column=1, pady=5, sticky="w")
    
    checkbox_vars.append(checkbox_var)


scrollable_frame.update_idletasks()  # Ensure all geometry updates are processed
canvas.configure(scrollregion=canvas.bbox("all")) 

#°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°#
#--------------------HELP PAGE------------------------#
#°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°#

help_tab = ttk.Frame(notebook)
notebook.add(help_tab, text="Help")

canvas = tk.Canvas(help_tab, bg="#f0f0f0")
scrollbar = tk.Scrollbar(help_tab, orient="vertical", command=canvas.yview)

scrollable_frame = tk.Frame(canvas, bg="#f0f0f0")

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

def on_mouse_wheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

canvas.bind("<MouseWheel>", on_mouse_wheel)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

header_label = tk.Label(scrollable_frame, text="Hotkeys for the CARLA Spectator Client", font=("Arial", 14, "bold"), justify="left")
header_label.pack(pady=5, padx=20, anchor="w")

header_label = tk.Label(scrollable_frame, text="Here are some hotkeys that you can use to navigate in the CARLA Spectator Client. This won't \n"
                        "work in the CARLA server.\n \n Hotkeys: \n   -q = quit: terminate the spectator client \n   -n = next: Switch to the next vehicle \n"
                        "   -o = overlay: toggle the overlay that shows the name of the HUD and the car \n    (does not toggle the configured HUD!)", font=("Arial", 12), justify="left")
header_label.pack(pady=5, padx=20, anchor="w")

# empty line
empty_label = tk.Label(scrollable_frame, text="")
empty_label.pack(pady=5, padx=20, anchor="w")  # Padding after the empty line


"""explanation of HUD elements"""
header_label = tk.Label(scrollable_frame, text="Explanation of Spectator HUD Icons", font=("Arial", 14, "bold"), justify="left")
header_label.pack(pady=5, padx=20, anchor="w")


image_frame = tk.Frame(scrollable_frame)
image_frame.pack(pady=10, padx=10, anchor="w")
imageicon1 = Image.open("icons\\stopwatch-svgrepo-com.png")
imageicon1 = imageicon1.resize((200, 200), Image.Resampling.LANCZOS)  # Adjust picture size
imageicon1_tk = ImageTk.PhotoImage(imageicon1)

imageicon1 = tk.Frame(image_frame)
imageicon1.pack(side="left", padx=20)

label_imageicon1 = tk.Label(imageicon1, image=imageicon1_tk)
label_imageicon1.pack(pady=10)

label_imageicon1 = tk.Label(imageicon1, text="Speedometer with updating vehicle speed", font=("Arial", 12))
label_imageicon1.pack(pady=10)

imageicon2 = Image.open(r"icons\battery-svgrepo-com.png")
imageicon2 = imageicon2.resize((200, 200), Image.Resampling.LANCZOS)  # Adjust picture size
imageicon2_tk = ImageTk.PhotoImage(imageicon2)

imageicon2 = tk.Frame(image_frame)
imageicon2.pack(side="left", padx=15)

label_imageicon2 = tk.Label(imageicon2, image=imageicon2_tk)
label_imageicon2.pack(pady=10)

label_imageicon2 = tk.Label(imageicon2, text="Current battery charge (for electric vehicle) (placeholder)", font=("Arial", 12))
label_imageicon2.pack(pady=10)

image_frame = tk.Frame(scrollable_frame)
image_frame.pack(pady=10, padx=10, anchor="w")
imageicon3 = Image.open("icons\\calendar-svgrepo-com.png")
imageicon3 = imageicon3.resize((200, 200), Image.Resampling.LANCZOS)  # Adjust picture size
imageicon3_tk = ImageTk.PhotoImage(imageicon3)

imageicon3 = tk.Frame(image_frame)
imageicon3.pack(side="left", padx=70)

label_imageicon3 = tk.Label(imageicon3, image=imageicon3_tk)
label_imageicon3.pack(pady=10)

label_imageicon3 = tk.Label(imageicon3, text="Current date (placeholder)", font=("Arial", 12))
label_imageicon3.pack(pady=10)

imageicon4 = Image.open("icons\\clock-svgrepo-com.png")
imageicon4 = imageicon4.resize((200, 200), Image.Resampling.LANCZOS)  # Adjust picture size
imageicon4_tk = ImageTk.PhotoImage(imageicon4)

imageicon4 = tk.Frame(image_frame)
imageicon4.pack(side="left", padx=100)

label_imageicon4 = tk.Label(imageicon4, image=imageicon4_tk)
label_imageicon4.pack(pady=10)

label_imageicon4 = tk.Label(imageicon4, text="Current time (placeholder)", font=("Arial", 12))
label_imageicon4.pack(pady=10)

image_frame = tk.Frame(scrollable_frame)
image_frame.pack(pady=10, padx=10, anchor="w")
imageicon5 = Image.open("icons\\compass-svgrepo-com.png")
imageicon5 = imageicon5.resize((200, 200), Image.Resampling.LANCZOS)  # Adjust picture size
imageicon5_tk = ImageTk.PhotoImage(imageicon5)

imageicon5 = tk.Frame(image_frame)
imageicon5.pack(side="left", padx=60)

label_imageicon5 = tk.Label(imageicon5, image=imageicon5_tk)
label_imageicon5.pack(pady=10)

label_imageicon5 = tk.Label(imageicon5, text="Current Orientation (placeholder)", font=("Arial", 12))
label_imageicon5.pack(pady=10)

imageicon6 = Image.open("icons\\idea-svgrepo-com.png")
imageicon6 = imageicon6.resize((200, 200), Image.Resampling.LANCZOS)  # Adjust picture size
imageicon6_tk = ImageTk.PhotoImage(imageicon6)

imageicon6 = tk.Frame(image_frame)
imageicon6.pack(side="left", padx=50)

label_imageicon6 = tk.Label(imageicon6, image=imageicon6_tk)
label_imageicon6.pack(pady=10)

label_imageicon6 = tk.Label(imageicon6, text="Current state of headlights (placeholder)", font=("Arial", 12))
label_imageicon6.pack(pady=10)

image_frame = tk.Frame(scrollable_frame)
image_frame.pack(pady=10, padx=10, anchor="w")
imageicon7 = Image.open("icons\\minus-svgrepo-com.png")
imageicon7 = imageicon7.resize((200, 200), Image.Resampling.LANCZOS)  # Adjust picture size
imageicon7_tk = ImageTk.PhotoImage(imageicon7)

imageicon7 = tk.Frame(image_frame)
imageicon7.pack(side="left", padx=60)

label_imageicon7 = tk.Label(imageicon7, image=imageicon7_tk)
label_imageicon7.pack(pady=10)

label_imageicon7 = tk.Label(imageicon7, text="Current speed limit (placeholder)", font=("Arial", 12))
label_imageicon7.pack(pady=10)

imageicon8 = Image.open("icons\\music-player-svgrepo-com.png")
imageicon8 = imageicon8.resize((200, 200), Image.Resampling.LANCZOS)  # Adjust picture size
imageicon8_tk = ImageTk.PhotoImage(imageicon8)

imageicon8 = tk.Frame(image_frame)
imageicon8.pack(side="left", padx=0)

label_imageicon8 = tk.Label(imageicon8, image=imageicon8_tk)
label_imageicon8.pack(pady=10)

label_imageicon8 = tk.Label(imageicon8, text="Music player / radio showing current song (placeholder)", font=("Arial", 12))
label_imageicon8.pack(pady=10)

image_frame = tk.Frame(scrollable_frame)
image_frame.pack(pady=10, padx=10, anchor="w")
imageicon9 = Image.open(r"icons\navigation-svgrepo-com.png")
imageicon9 = imageicon9.resize((200, 200), Image.Resampling.LANCZOS)  # Adjust picture size
imageicon9_tk = ImageTk.PhotoImage(imageicon9)

imageicon9 = tk.Frame(image_frame)
imageicon9.pack(side="left", padx=70)

label_imageicon9 = tk.Label(imageicon9, image=imageicon9_tk)
label_imageicon9.pack(pady=10)

label_imageicon9 = tk.Label(imageicon9, text="Navigation (placeholder)", font=("Arial", 12))
label_imageicon9.pack(pady=10)

imageicon10 = Image.open("icons\\placeholder-svgrepo-com.png")
imageicon10 = imageicon10.resize((200, 200), Image.Resampling.LANCZOS)  # Adjust picture size
imageicon10_tk = ImageTk.PhotoImage(imageicon10)

imageicon10 = tk.Frame(image_frame)
imageicon10.pack(side="left", padx=70)

label_imageicon10 = tk.Label(imageicon10, image=imageicon10_tk)
label_imageicon10.pack(pady=10)

label_imageicon10 = tk.Label(imageicon10, text="Current geolocation (placeholder)", font=("Arial", 12))
label_imageicon10.pack(pady=10)


image_frame = tk.Frame(scrollable_frame)
image_frame.pack(pady=10, padx=10, anchor="w")
imageicon11 = Image.open(r"icons\smartphone-svgrepo-com.png")
imageicon11 = imageicon11.resize((200, 200), Image.Resampling.LANCZOS)  # Adjust picture size
imageicon11_tk = ImageTk.PhotoImage(imageicon11)

imageicon11 = tk.Frame(image_frame)
imageicon11.pack(side="left", padx=40)

label_imageicon11 = tk.Label(imageicon11, image=imageicon11_tk)
label_imageicon11.pack(pady=10)

label_imageicon11 = tk.Label(imageicon11, text="Smartphone connection (placeholder)", font=("Arial", 12))
label_imageicon11.pack(pady=10)

imageicon12 = Image.open("icons\\speaker-svgrepo-com.png")
imageicon12 = imageicon12.resize((200, 200), Image.Resampling.LANCZOS)  # Adjust picture size
imageicon12_tk = ImageTk.PhotoImage(imageicon12)

imageicon12 = tk.Frame(image_frame)
imageicon12.pack(side="left", padx=100)

label_imageicon12 = tk.Label(imageicon12, image=imageicon12_tk)
label_imageicon12.pack(pady=10)

label_imageicon12 = tk.Label(imageicon12, text="Music volume (placeholder)", font=("Arial", 12))
label_imageicon12.pack(pady=10)


# empty line
empty_label = tk.Label(scrollable_frame, text="")
empty_label.pack(pady=5, padx=20, anchor="w")  # Padding after the empty line


# Header on the help tab
empty_label.pack(pady=5, padx=20, anchor="w") 

header_label = tk.Label(scrollable_frame, text="Setting a HUD for simulation", font=("Arial", 14, "bold"), justify="left")
header_label.pack(pady=5, padx=20, anchor="w")

header_label = tk.Label(scrollable_frame, text="Probability", font=("Arial", 14, "bold"), justify="left")
header_label.pack(pady=5, padx=20, anchor="w")

header_label = tk.Label(scrollable_frame, text="You can use the probability field to change the probability of the specific HUD getting simulated in the \n simulation."
                        "The probability is set in fractions, not percentage! Please make sure to enter an Integer > 0.", font=("Arial", 12), justify="left")
header_label.pack(pady=10, padx=20, anchor="w")

header_label = tk.Label(scrollable_frame, text="Brightness", font=("Arial", 14, "bold"), justify="left")
header_label.pack(pady=10, padx=20, anchor="w")

description_label = tk.Label(scrollable_frame, text=(
    "The brightness level represents how visible the HUD will be for the driver. \n" 
    "The options are: \n"
    "   - very dark \n"
    "   - dark \n"
    "   - average \n"
    "   - bright \n"
    "   - very bright \n"
    "While the option 'very dark' will make the HUD extremely visible, the option 'very bright' makes the \n HUD almost see-through."
), font=("Arial", 12), justify="left")
description_label.pack(pady=10, padx=20, anchor="w")

image1 = Image.open("screenshots\\hud-brightness-very-bright.png")
image1 = image1.resize((340, 200), Image.Resampling.LANCZOS)
image1_tk = ImageTk.PhotoImage(image1)

image2 = Image.open("screenshots\\hud-brightness-very-dark.png")
image2 = image2.resize((340, 200), Image.Resampling.LANCZOS)
image2_tk = ImageTk.PhotoImage(image2)

image_frame = tk.Frame(scrollable_frame)
image_frame.pack(pady=10, padx=10, anchor="w")

frame1 = tk.Frame(image_frame)
frame1.pack(side="left", padx=20)

label_image1 = tk.Label(frame1, image=image1_tk)
label_image1.pack(pady=10)

label_desc1 = tk.Label(frame1, text="Brightness level: 'very bright'", font=("Arial", 12))
label_desc1.pack(pady=10)

frame2 = tk.Frame(image_frame)
frame2.pack(side="left", padx=20)

label_image2 = tk.Label(frame2, image=image2_tk)
label_image2.pack(pady=5)

label_desc2 = tk.Label(frame2, text="Brightness level: 'very dark'", font=("Arial", 12))
label_desc2.pack(pady=10)

header_label = tk.Label(scrollable_frame, text="Field of View", font=("Arial", 14, "bold"), justify="left")
header_label.pack(pady=10, padx=20, anchor="w")

description_label = tk.Label(scrollable_frame, text=(
    "The Field of View (FoV) defines the position of the information on the windshield.\n" 
    "The options are: \n"
    "   - small \n"
    "   - medium \n"
    "   - large \n"
    "A large FoV projects elements directly in the driving environment exploiting the size of the whole \n simulated windshield while a small FoV means that items are placed above the steering \n wheel with a fixed location and less space for information presentation."
), font=("Arial", 12), justify="left")
description_label.pack(pady=10, padx=20, anchor="w")

image12 = Image.open("screenshots\\hud-fov-small.png")
image12 = image12.resize((340, 200), Image.Resampling.LANCZOS) 
image12_tk = ImageTk.PhotoImage(image12)

image22 = Image.open("screenshots\\hud-fov-large.png")
image22 = image22.resize((340, 200), Image.Resampling.LANCZOS) 
image22_tk = ImageTk.PhotoImage(image22)

image_frame = tk.Frame(scrollable_frame)
image_frame.pack(pady=10, padx=10, anchor="w")

frame12 = tk.Frame(image_frame)
frame12.pack(side="left", padx=20)

label_image12 = tk.Label(frame12, image=image12_tk)
label_image12.pack(pady=10)

label_desc12 = tk.Label(frame12, text="FoV: 'small'", font=("Arial", 12))
label_desc12.pack(pady=10)

frame22 = tk.Frame(image_frame)
frame22.pack(side="left", padx=20)

label_image22 = tk.Label(frame22, image=image22_tk)
label_image22.pack(pady=5)

label_desc22 = tk.Label(frame22, text="FoV: 'large'", font=("Arial", 12))
label_desc22.pack(pady=10)

header_label = tk.Label(scrollable_frame, text="Information relevance", font=("Arial", 14, "bold"), justify="left")
header_label.pack(pady=10, padx=20, anchor="w")

description_label = tk.Label(scrollable_frame, text=(
    "The information relevance describes the average relevance level of the \n information that is being displayed." 
    "The options are: \n"
    "   - unimportant \n"
    "   - neutral \n"
    "   - important \n"
    "'important' means that only important information like the speed of the driver, the speed limit and navigation \n instruction will be displayed on the HUD while 'unimportant' will also represent \n information about your music player or the temperature outside "
), font=("Arial", 12), justify="left")
description_label.pack(pady=10, padx=20, anchor="w")

image13 = Image.open("screenshots\\hud-relevance-unimportant.png")
image13 = image13.resize((340, 200), Image.Resampling.LANCZOS) 
image13_tk = ImageTk.PhotoImage(image13)

image23 = Image.open("screenshots\\hud-relevance-important.png")
image23 = image23.resize((340, 200), Image.Resampling.LANCZOS)
image23_tk = ImageTk.PhotoImage(image23)

image_frame = tk.Frame(scrollable_frame)
image_frame.pack(pady=10, padx=10, anchor="w")

frame13 = tk.Frame(image_frame)
frame13.pack(side="left", padx=20)

label_image13 = tk.Label(frame13, image=image13_tk)
label_image13.pack(pady=10)

label_desc13 = tk.Label(frame13, text="Information relevance: 'unimportant'", font=("Arial", 12))
label_desc13.pack(pady=10)

frame23 = tk.Frame(image_frame)
frame23.pack(side="left", padx=20)

label_image23 = tk.Label(frame23, image=image23_tk)
label_image23.pack(pady=5)

label_desc23 = tk.Label(frame23, text="Information relevance: 'important'", font=("Arial", 12))
label_desc23.pack(pady=10)

header_label = tk.Label(scrollable_frame, text="Information frequency", font=("Arial", 14, "bold"), justify="left")
header_label.pack(pady=10, padx=20, anchor="w")

description_label = tk.Label(scrollable_frame, text=(
    "The information frequency describes when the information is displayed on the windshield. \n" 
    "The options are: \n"
    "   - minimum \n"
    "   - average \n"
    "   - maximum \n"
    "'minimum' means the information is only being displayed when needed to 'maximum' means all \n available information is always displayed."
), font=("Arial", 12), justify="left")
description_label.pack(pady=10, padx=20, anchor="w")

image14 = Image.open("screenshots\\hud-all-min.png")
image14 = image14.resize((340, 200), Image.Resampling.LANCZOS)
image14_tk = ImageTk.PhotoImage(image14)

image24 = Image.open("screenshots\\hud-all-max.png")
image24 = image24.resize((340, 200), Image.Resampling.LANCZOS) 
image24_tk = ImageTk.PhotoImage(image24)

image_frame = tk.Frame(scrollable_frame)
image_frame.pack(pady=10, padx=10, anchor="w")

frame14 = tk.Frame(image_frame)
frame14.pack(side="left", padx=20)

label_image14 = tk.Label(frame14, image=image14_tk)
label_image14.pack(pady=10)

label_desc14 = tk.Label(frame14, text="Information frequency: 'minimum'", font=("Arial", 12))
label_desc14.pack(pady=10)

frame24 = tk.Frame(image_frame)
frame24.pack(side="left", padx=20)

label_image24 = tk.Label(frame24, image=image24_tk)
label_image24.pack(pady=5)

label_desc24 = tk.Label(frame24, text="Information frequency: 'maximum'", font=("Arial", 12))
label_desc24.pack(pady=10)

scrollable_frame.update_idletasks() 
canvas.configure(scrollregion=canvas.bbox("all"))


#°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°#
#---------------MAIN PAGE--------------------#
#°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°#

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

hudless_checkbox = tk.Checkbutton(main_tab, text="Simulate a car that is not using a HUD. \n"" The HUD probability is always 5.", variable=hudless_var, font=('Helvetica', 12))
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
