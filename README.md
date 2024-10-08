
# Simulating the effects of AR windshield HUDs on driving performance using SUMO and CARLA

![Software overview diagram](/screenshots/diagram.png)

## Introduction
### Simulating the effects of AR windshield HUDs on driving performance using SUMO and CARLA

[SUMO](https://www.eclipse.org/sumo/) (Simulation of Urban MObility)  is "an open source, highly portable, microscopic and 
continuous multi-modal traffic simulation package designed to handle large networks" (https://www.eclipse.org/sumo/).

[CARLA](https://carla.org/) is an "Open-source simulator for autonomous driving research". (https://carla.org/)

This project is about the effect that Augmented Reality Head Up Displays (AR-HUDs) have on the driving performance of drivers in an urban environment. Using SUMO, it is possible to simulate how driving behavior changes in response to different AR-HUDs, for example by influencing the awareness of the surrounding vehicles or reaction times to events happening nearby. If an AR-HUD has a high distraction level, it has an negative influence to the reaction time of the driver, while an AR-HUD with a low distraction level but high relevance of informations can improve the reaction time. Those changes can be observed in a 3D environment using CARLA, which makes it easier to observe situations and evaluate them.
We always tried to make factors (calculations, values, etc) impacting the driving performance as reasonable and factual as possible using scientific resources whenever possible or making educated guesses.


## Frameworks and Libraries
* Sumo (Version 1.20)
  * traci (python package)
  * sumolib (python package)
* CARLA (Version 0.9.15)
  * carla (python package)
* Python 3 (Version 3.10)
* tkinter (for GUI)
* numpy, cv2 (for live feed overlays)
* cElementTree, minidom (for xml operations)
* PIL (for picture integration)
* XML, CSV (file formats)

Generally, we try to use the latest version of each package und Framework to improve speed and accuracy. However, the carla python package is only available for python 3.10 or older, limiting the python version. Using older libraries should be compatible.


## Installation

### Requirements / Pre-installation
* [Python 3.10](https://www.python.org/downloads/)
* [Sumo 1.20](https://sumo.dlr.de/docs/Downloads.php)
* [Carla 0.9.15](https://carla.readthedocs.io/en/0.9.15/download/)

### Setup
1. Make sure that all requirements are installed and the PATH variable is correctly set.
2. Clone this repository to a location of your choice.
3. Install python packages using pip.

```
pip install -r .\requirements.txt
```

4. Open "config.py" and setup your carla base path up to the folder "\WindowsNoEditor".
5. Copy content of setup_files into the Carla folder (copy the WindowsNoEditor folder over the one from carla, merge/ overwrite if promted)

### Update .rou files
* For the simulation to work you need to update the .rou.xml files in your CarlaBaseDir/Co-Simulation/Sumo/examples/rou folder.
* You can either use the files provided with this project or create your own files using randomTrips.py.
* You can find the method in the /tools folder in your SUMO installation.

```
python randomTrips.py -n "CarlaBaseDir/Co-Simulation/Sumo/examples/net/TownXX.net.xml" -e 7200 --route-file "CarlaBaseDir/Co-Simulation/Sumo/examples/rou/Townxx.rou.xml" --period 6 --validate 
```
* Using this command you will get the appropriate .rou file for the simulation. 
* You can change the duration of your simulation by setting the -e to a different value.
* Please make sure to also set  --period <FLOAT> (default 1) to your prefered value. 
  Note: Setting --period too low will cause the simulation to become overflooded which prevents the simulation from running correctly. You can avoid this by choosing a higher --period value.

### Running the Software
1. Run main.py to access the GUI ("python main.py")
2. In the GUI, select which components u want to run.
    1. choose a map for the simulation from the list
    2. select wether you want the co-simulation with CARLA, run the first-person spectator client and wether you want a vehicle without a HUD (a baseline vehicle). If you select the first-person spectator client without the CARLA option, a silent CARLA server will start in the background.
    3. Add or remove HUD configurations until you have the desired number.
    4. configure and adjust probability and name of all HUD configurations
    * If you want to run the spectator client at a later point, make sure you selected the co-simulation with Carla option and run spectator.py
3. click start Simulation. SUMO and other selected components will open for a visual simulation. Simultaniously TRaCI will run the simulation in the background and collect all data.
4. The simulation results will be saved to the folder [Simulation_data](./Simulation_data)

You can start the next simulation without having to restart the project. Just make sure to close all running SUMO and CARLA processes before starting a new simulation. Sometimes a CARLA thread doesn't close properly and idles in the background which causes problems when trying to start a new simulation. If you have issues starting a new simulation check the taskmanager and close all running CARLA threads.

![GUI with main tab](/screenshots/GUI_main.PNG)

### Keybinds spectator:

* q = Quit: Terminate the Spectator Client.
* n = Next: Switch to the next vehicle
* o = Overlay: Toggle the overlay that shows the name of the HUD and car (does not toggle the configured HUD!).

### Configurations

After opening the GUI you can navigate to the settings tab. Here you can select which simulation data you would like to save in your .csv file.
Note that by default all the data is selected. Everytime you restart the GUI you have the manually deselect options you don't want to save.

These are the options:
* map: the map that was being used for the simulation
* vehicle_id: unique vehicle id 
* hud_id: unique hud_id in the form of: individualIdentifier_HUDname 
* simulation_time: the simulation step when the data was being collected
* vehicle_type: the vehicle_type the car is using
* position_x: x position of the vehicle
* position_y: y position of the vehicle
* current_speed: current speed of the vehicle
* current_gap: current gap of the vehicle to the leading vehicle
* current_acceleration: current acceleration of the vehicle, negative values means the vehicle is braking
* distance_traveled: total distance the vehicle has traveled during the simulation
* time_loss: total time the car is behind its schedule
* maxSpeed: calculated maximal speed the car will drive
* speedAdherenceFactor: calculated factor to which the car follows the speed limit
* reactionTime: calculated reaction time for the HUD
* fatiguenessLevel: calculated fatigueness level for the HUD
* awarenessLevel: calculated awareness level for the HUD
* acceleration: calculated maximal acceleration for the HUD
* minGapFactor: calculated factor to which the driver obeys the legal minimal gap
* distractionLevel: calculated distraction level for the HUD
* brightness: brightness option that was selected for the HUD
* information_frequency: information frequency that was selected for the HUD
* information_relevance: information relevance that was selected for the HUD
* FoV: FoV option that was selected for the HUD

Note that you are not able to deselect the hud_id. 

![GUI with settings tab](/screenshots/GUI_settings.PNG)

## Files overview:
        Apse-Extension-for-Carla-and-Sumo
        |---icons : Folder that contains the Icons used as HUD elements in the spectator client 
        |    |---12 icon image files
        |---screenshots : Folder that contains screenshots from the components for use in the docs and help page
        |    |---13 screenshots
        |---setup_files : Folder that contains the path and the files that need to be updated within Carla for the program to run
        |    |---root_folder_of_carla
        |          |---WindowsNoEditor
        |               |---Co-Simulation
        |                    |---Sumo
        |                         |---examples
        |                              |---rou
        |                                   |---Town01.rou.xml : Route file for map Town01, required for vehicles to be simulated in Carla
        |                                   |---Town04.rou.xml : Route file for map Town04, required for vehicles to be simulated in Carla
        |                                   |---Town05.rou.xml : Route file for map Town05, required for vehicles to be simulated in Carla
        |---Simulation_data : Folder that contains all generated simulation data, empty by default.
        |---calculations.py : File that contains all simulation formulas.
        |---config.py : Configuration file that contains the path to the Carla folder.
        |---hudconfig.xml : File that contains the HUD config of the last simulation, used to transfer HUD settings from the main client to the spectator client.
        |---main.py : File that contains the main client, used to start all other components and configure all HUDs.
        |---README.md : Readme that contains a overview over all files and instructions to run the program.
        |---requirements.txt : File that contains the python packages that are used and are not included in the default python installation.
        |---spectator.py : File that contains the spectator client, used to spectate Cars from a driver perspective and show an example HUD based on the HUD configuration.


## Limitations
There are several limitations to this project:

* Options used to simulate the AR HUDs are very limited. To allow a more accurate simulation it would be necessary to differentiate more, maybe even allow the costumisation of the different HUD elements.
* The created formulae, base values and weights used to simulate the driving performance with the use of AR HUDs are based on data from the linked research. However the accuracy of the simulation results can be decreased if the data is imprecisely or scarce regarding certain factors. We tried to use as much data as possible but some calculations are educated guesses.
* The number of HUDs that is being simulated at the same time is limited to the amount of available vehicle types (vTypes) in CARLA since the different HUDs are being mapped to the vTypes. Currently we are enabling simulating eleven HUDs at the same time.
* CARLA has rather large requirements for self-compiling that made it not feasible for us to modify CARLA directly. Therefore, we were forced to use a pre-compiled version of CARLA that works good in itself, but imposes restrictions on the overall project.
* The SUMO integration into CARLA is usable to show the state of vehicles in an 3D environment, but making use of the plethora of sensors and tools that CARLA can provide was not possible. The vehicle data is transferred in a way of SUMO providing the location of every vehicle at every given time to CARLA, meaning the sensors only see the vehicle projection with no access to the simulation data itself.
* The spectator client is limited in information that it receives because the CARLA sensors don't work properly. Therefore, the visualization is a lot less dynamic than it could have been. The spectator client is pretty much limited to the vehicle speed as an dynamic item in the HUD.
* While SUMO and CARLA synchronize the vehicles pretty well, there are consistency and synchronization errors between SUMO and CARLA regarding the world, for example traffic lights are not in sync and roadsigns don't necessarily match.
* There is no proper way to export maps from SUMO to CARLA, as CARLA maps require extensive 3D modelling of the complete map.This limited us to the maps that are provided by CARLA.


#### Icon source:

* https://www.svgrepo.com/collection/essential-set-2/