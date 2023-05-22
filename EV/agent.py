"""This module contains the agent classes for the EV model."""
import numpy as np
import math
import random

import warnings
warnings.simplefilter("ignore")
import numpy as np
from mesa import Agent

from transitions import Machine, MachineError
from EV.statemachines import EVSM, LSM, states, transitions, lstates, ltransitions
import EV.worker as worker
import logging
import EV.model_config as cfg
# import cufflinks as cf
# cf.go_offline()
# from functools import partial
# from random import choice

logger = logging.getLogger(__name__)

class ChargeStation(Agent):
    """A charging station (CS) agent.
    Attributes:
        unique_id: Unique identifier for the agent.
        model: A reference to the model object.
        queue: A list of EVs waiting to charge.
        occupied_cps: A set of occupied charge points.
        no_cps: Number of charge points at the CS.
        _is_active: Boolean indicating whether the CS is active.
        # _charge_rate: The charge rate of the CS.
        # checkpoint_id: The ID of the checkpoint.
        route: The route of the CS.
        cplist: The list of charge points at the CS.
        name: The name of the CS.
        pos: The position of the CS.
        #cprates: The list of charge rates of the charge points at the CS.
        location_occupancy: The number of EVs currently at the CS.
        location_occupancy_list: The list of EVs currently at the CS.


    Methods:
        __init__: Initialises the agent.
        dequeue_ev: Removes the first EV from the queue.
        finish_charge_ev: Finish charging the EV at the ChargeStation.
        stage_1: Stage 1 of the agent's step function.
        stage_2: Stage 2 of the agent's step function.

    """
    def __init__(self, unique_id, model): #rem: no_cps,
        super().__init__(unique_id, model)
        # Start initialisation
        self.queue = []
        self.occupied_cps = set()
        self.no_cps = 0
        self._is_active = False
        self.checkpoint_id = 0 # was 0 

        # new
        self.route = None
        self.cplist = None
        self.name = None
        self.pos = None
        self.cprates = []  #kW
        self._charge_rate = 0
        self.location_occupancy = 0
        self.location_occupancy_list =[]
        self.prelim_report()
        # End initialisation
    
    def prelim_report(self):
        """Prints a preliminary report of the agent's attributes."""
        # print(f"CS {(self.unique_id)}, initialized.")
        logging.info(f"CS {(self.unique_id)}, initialized.")

    def init_report(self):
        """Prints a report of the agent's attributes."""
        # print(f"\nCS info: ID: {(self.unique_id)}, initialized. Charge rates for charge points: {self.cprates} kW.")
        # print(f"It has {self.no_cps} charging points.")
        logging.info(f"\nCS info: ID: {(self.unique_id)}, initialized. Charge rates for charge points: {self.cprates} kW.")
        logging.info(f"It has {self.no_cps} charging points.")
        for i in range(self.no_cps):
            print(f"CP_{i} is {(getattr(self, f'cp_id_{i}'))}")

    def dequeue(self, model) -> bool:
        """Remove the first EV from queue."""
        try:
            active = self.queue.pop(0)  # pick first EV in queue
            if active is None:
                return False
            
            # go through all charge points and assign the first one that is free
            for attr_name in [a for a in dir(self) if a.startswith("cp_")]:
            # for attr_name in [a for a in dir(self) if isinstance(getattr(self, a), ChargePoint)]:
                attr_value = getattr(self, attr_name)
                if attr_value is None:
                    setattr(self, attr_name, active)
                    active.machine.start_charge()
                    self.occupied_cps.add(attr_name)
                    # print(f"EV {active.unique_id} dequeued at {self.name} at {attr_name} and is in state: {active.machine.state}. Charging started")
                    logging.info(f"EV {active.unique_id} dequeued at {self.name} at {attr_name} and is in state: {active.machine.state}. Charging started")
                    route_rates = worker.get_power_values_route(station_config=model.station_params, route_name=self.route)
                    print("\n")
                    # print(f"CS name: {self.name}, Route charge rates: {route_rates}, CP number: {worker.cp_name_to_cp_number(attr_name)}")
                    # Set EV charge rate
                    active.charge_rate = worker.get_cp_value(route_rates, self.name, worker.cp_name_to_cp_number(attr_name))
                    # print(f"EV {active.unique_id} has been assigned to {attr_name} at {self.name}. State: {active.machine.state}. Charge rate: {active.charge_rate} kW.")
                    logging.info(f"EV {active.unique_id} has been assigned to {attr_name} at {self.name}. State: {active.machine.state}. Charge rate: {active.charge_rate} kW.")
                    return True
                elif attr_value is not None:
                    # print(f"Charge point {attr_name} at {self.name} is occupied.")
                    logging.info(f"Charge point {attr_name} at {self.name} is occupied.")
            # if all charge points are occupied, reinsert active EV into queue
            self.queue.insert(0, active)
            # print(f"EV {active.unique_id} remains in queue at CS {self.name} and is in state: {active.machine.state}.")
            logging.info(f"EV {active.unique_id} remains in queue at CS {self.name} and is in state: {active.machine.state}.")
            return False
        except IndexError:
            # print(f"The queue at ChargeStation {self.unique_id} is empty.")
            logging.info(f"The queue at ChargeStation {self.name} is empty.")
            return False
        except Exception as e:
            print(f"Error assigning EV to charge point: {e}")
            logging.warning(f"Error assigning EV to charge point: {e}")
            return False
   
    def finish_charge(self) -> None:
        """Finish charging the EV at the ChargeStation."""
        try:
            for attr_name in dir(self):
                if attr_name.startswith("cp_"):
                    attr_value = getattr(self, attr_name)
                    if attr_value is None:
                        # print(f"CP {attr_name} at ChargeStation {self.unique_id} is vacant.")
                        # pass
                        return None
                    else:
                        if attr_value.machine.state == 'Charge' and (attr_value.battery < attr_value._soc_charging_thresh):
                            attr_value.machine.continue_charge()
                            attr_value.calculate_soc()
                            # print(f"EV {attr_value.unique_id} at CS {self.name} at {attr_name} is in state: {attr_value.machine.state}. SOC: {attr_value.soc:.2f}%, Battery: {attr_value.battery:.2f} kWh.")
                            logging.info(f"EV {attr_value.unique_id} at CS {self.name} at {attr_name} is in state: {attr_value.machine.state}. SOC: {attr_value.soc:.2f}%, Battery: {attr_value.battery:.2f} kWh.")
                        elif attr_value.machine.state == 'Idle':
                            # self.remove_ev(attr_value)
                            attr_value._at_station = False
                            self.occupied_cps.remove(attr_name)
                            self.location_occupancy_list.remove(attr_value.unique_id)
                            self.location_occupancy -= 1
                            # print(f"EV {attr_value.unique_id} at CS {self.name} at {attr_name} has had charging interrupted. EV removed.")
                            logging.info(f"EV {attr_value.unique_id} at CS {self.name} at {attr_name} has had charging interrupted. EV removed.")
                            setattr(self, attr_name, None)
                        elif attr_value.machine.state == 'Charge' and (attr_value.battery >= attr_value._soc_charging_thresh):
                            # new change
                            attr_value.machine.end_charge()
                            attr_value._is_charging = False
                            attr_value.calculate_soc()
                            # print(f"EV {attr_value.unique_id} has finished charging. EV State: {attr_value.machine.state}. SOC: {attr_value.soc}%, Current charge: {attr_value.battery:.2f} kWh.")
                            logging.info(f"EV {attr_value.unique_id} has finished charging. EV State: {attr_value.machine.state}. SOC: {attr_value.soc}%, Current charge: {attr_value.battery:.2f} kWh.")
                            attr_value._at_station = False
                            self.occupied_cps.remove(attr_name)
                            self.location_occupancy_list.remove(attr_value.unique_id)
                            self.location_occupancy -= 1
                            # self.remove_ev(ev=attr_value) #doesnt work, cant reach CP using function, OOL. Use repitition temporarily.
                            # print(f"EV {attr_value.unique_id} at CS {self.name} at {attr_name} has finished charging. EV departed.")
                            logging.info(f"EV {attr_value.unique_id} at CS {self.name} at {attr_name} has finished charging. EV departed.")
                            setattr(self, attr_name, None)
                            # print(f"CP is now free to use.")
                            logging.info(f"CP is now free to use.")
        except AttributeError as A:
            # print(f"CP unavailable. Reason: {A}")
            logging.warning(f"CP unavailable. Reason: {A}")
            
    # def remove_ev(self,ev):
    #     ev._at_station = False
    #     print("Flag change executed.")
    #     self.occupied_cps.remove(ev) #attr name, not value. From Cp, not EV
    #     self.location_occupancy_list.remove(ev.unique_id)
    #     self.location_occupancy -= 1

    def stage_1(self):
        """Stage 1 of the charge station's step function."""
        if len(self.queue) > 0:
            for ev in self.queue:
                print(f"EV {ev.unique_id} is in queue at CS {self.name}. EV state: {ev.machine.state}.")
                logging.info(f"EV {ev.unique_id} is in queue at CS {self.name}. EV state: {ev.machine.state}.")
        self.dequeue(self.model)

    def stage_2(self):
        """Stage 2 of the charge station's step function."""
        self.finish_charge()
  
class EV(Agent):
    """An agent used to model an electric vehicle (EV).
    Attributes:
        unique_id: Unique identifier for the agent.
        model: Model object that the agent is a part of.
        charge_rate: Charge rate of the EV in kW.
        _in_queue: Whether the EV is in the queue at a charge station. Bool flag. 
        _in_garage: Whether the EV is in the garage at the driver's home. Bool flag. 
        _is_charging: Whether the EV is charging. Bool flag.
        _was_charged: Whether the EV was charging. Bool flag. 
        _at_station: Whether the EV is at a charge station. Bool flag
        _is_travelling: Whether the EV is travelling.
        _journey_complete: Whether the EV has completed its journey. Bool flag.
        _is_active: Whether the EV is active. Bool flag.
        route: The route the EV is taking.
        machine: The main state machine of the EV. The state of charge state machine of the EV.
        loc_machine: The location state machine of the EV.
        odometer: The odometer of the EV.
        _distance_goal: The distance the EV needs to travel to reach its destination.
        journey_type: The type of journey the EV is undertaking.
        source: The source of the EV.
        destination: The destination of the EV.
        battery: The current charge level of the EV battery.
        soc: The state of charge of the EV.
        max_battery: The maximum battery capacity of the EV.
        range_anxiety: The range anxiety of the EV.
        _soc_usage_thresh: The state of charge threshold at which the EV will start looking for a charge station.
        _soc_charging_thresh: The state of charge threshold at which the EV will stop charging.
        ev_consumption_rate: The energy consumption rate of the EV.
        tick_energy_usage: The energy usage of the EV in a tick.
        battery_eod: The state of charge of the EV at the end of the day.
        start_time: The start time of the EV.
        _chosen_cs: The chosen charge station of the EV.
        checkpoint_list: The list of checkpoints the EV will pass through.
        pos: The position of the EV. Tuple containing x and y coordinates.
        locations: Given the model, the locations the EV can travel to.
        dest_pos: The position of the destination of the EV. Tuple containing x and y coordinates.
        home_cs_rate: The charge rate of the EV at its home charge station.


    Methods:
        __init__: Initialise the EV agent.
        __str__: Return the agent's unique id, +1 to make it readable.
        initialization_report: Print the details of the agent's initial state.
        set_source_loc_mac_from_route: Set the initial location state machine of the EV, using its source from route.
        update_loc_mac_from_destination: Update the location state machine of the EV.
        # set_initial_soc_mac_from_battery: Set the initial state of charge state machine of the EV.
        get_initial_location_from_route: Get the location of the EV from its route.
        get_destination_from_route: Get the destination of the EV from its route.
        update_destination_for_new_trip: Update the destination of the EV for a new trip.
        # update_destination_for_new_day: Update the destination of the EV for a new day.
        
        set_speed: Set the speed of the EV.
        set_ev_consumption_rate: Set the energy consumption of the EV.
        energy_usage_trip: Energy usage of the EV in a trip.
        energy_usage_tick: Energy usage of the EV in a tick.
        delta_battery_neg: Calculate the change in state of charge of the EV.

        dead_intervention: Intervene if the EV is dead at the end of the day. Recharge the EV to max.
        travel_intervention: Intervene if the EV is travelling at the end of the day. Stop the EV, transport it to its destination.
        charge_intervention: Intervene if the EV is charging at the end of the day. Stop the charging, transport it to its destination.
        set_start_time: Set the start time of the EV.
        
        increase_range_anxiety: Increase the range anxiety of the EV.
        decrease_range_anxiety: Decrease the range anxiety of the EV.

        select_initial_coord: Select the initial coordinates of the EV from the model's locations.
        select_destination_coord: Select the destination coordinates of the EV from the model's locations.
        set_destination: Set the destinations of the EV.
        get_distance_goal_and_coord_from_dest: Get the distance goal and coordinates of the EV from its destination.
        move: Move the EV to its destination.
        update_lsm: Update the location state machine of the EV.
        travel: Travel function for the EV agent.
        search_for_charge_station: Search for a charge station.
        charge: Charge the EV while it is at a charge station.
        charge_overnight: Charge the EV overnight at its home charge station.
        join_cs_queue: Join the queue at the charge station.
        
        dailies:
        add_soc_eod: Add the state of charge of the EV at the end of the day to a list.
        reset_odometer: Reset the odometer of the EV.
        relaunch_base: Base EV relaunch process.
        relaunch_travel: Relaunch process for travelling EVs.
        relaunch_charge: Relaunch process for charging EVs.
        relaunch_dead: Relaunch process for dead EVs.
        relaunch_idle: Relaunch process for idle EVs.
        start_travel: Start the travel process for the EV at the allocated start time.
        euc_distance: Calculate the euclidean distance between two points.
    
        step functions:
        stage_1: Stage 1 of the agent step function. Handles the EV's journey.
        stage_2: Stage 2 of the agent step function. Handles the EV's charging.

        unused:

        tick_energy_usage: Energy usage of the EV in a tick.
        battery_eod: State of charge of the EV at the end of the day.
        day_count: Number of days the EV has been active.

        TO-DO
        pull from params:
        charge rate, distance, price, green


        
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        # EV attributes
        self.charge_rate = 0
        self._in_queue = False
        self._in_garage = False
        self._is_charging = False
        self._was_charged = False
        self._at_station = False
        self._is_travelling = False
        self._journey_complete = False
        self._is_active = True
        self.route = None
        self.machine = EVSM(initial='Idle', states=states, transitions=transitions)
        self.loc_machine = LSM(initial='City_A', states=lstates, transitions=ltransitions)
        self.odometer = 0
        self._distance_goal = 0 
        self.distance_margin = 0
        self.static_distance_goal = 0
        self.step_distance = 0
        self.start_time = 0
        self._chosen_cs = None
        self.checkpoint_list = []
        
        # set EV speed
        self.set_speed()
        # set energy consumption rate
        self.set_ev_consumption_rate()

        # Location attributes
        self.source = None
        self.destination = None

        # energy
        self.battery = random.randint(40, 70) #kWh (40, 70) 
        self.max_battery = self.battery
        self.soc = 0
        self.range_anxiety = 0.5    #likelihood to charge at charge station 
        # battery soc level at which EV driver feels compelled to start charging at station.
        self._soc_usage_thresh = (self.range_anxiety * self.max_battery) 
        # battery soc level at which EV driver is comfortable with stopping charging at station.
        self._soc_charging_thresh = (0.8 * self.max_battery) 
        self.ev_consumption_rate = 0
        self.tick_energy_usage = 0
        self.battery_eod = []
        mu, sigma = 0.05, 0.1 # mean and standard deviation
        self.margin = np.random.default_rng().normal(mu, sigma)
        mu2, sigma2 = 0.01, 0.01 # mean and standard deviation
        self.dec_margin= np.random.default_rng().normal(mu2, sigma2)
    
        # mobility
        self.pos = None
        self.current_location = None
        self.locations = []
        self.dest_pos = None
        # Home Charging Station 
        self.home_cs_rate = 10 #kW
 
        # Initialisation Report
        self.prelim_report()
        # self.initalization_report()

        # EV Driver Behaviour policy parameters
    
    # Reporting functions
    def __str__(self) -> str:
        """Return the agent's unique id as a string, not zero indexed."""
        return str(self.unique_id + 1)
    
    def prelim_report(self):
        """Prints the EV's preliminary report."""
        print(f"EV {(self.unique_id)}, initialized.")

    def initialization_report(self, model) -> None:
        """Prints the EV's initialisation report."""
        # print(f"\nEV info: ID: {self.unique_id}, max_battery: {self.max_battery:.2f}, energy consumption rate: {self.ev_consumption_rate}, speed: {self._speed}, State: {self.machine.state}.")
        # print(f"EV info (Cont'd): Start time: {self.start_time},  soc usage threshold: {self._soc_usage_thresh}, range anxiety {self.range_anxiety}.")
        # print(f"EV Grid info: current position: {self.pos}, destination position: {self.dest_pos}, Distance goal: {self._distance_goal}.")        
        # print(f"Location info: current location (LSM): {self.loc_machine.state}, source: {self.source}, destination: {self.destination}, route: {self.route}.")
        logging.info(f"\nEV info: ID: {self.unique_id}, max_battery: {self.max_battery:.2f}, energy consumption rate: {self.ev_consumption_rate}, speed: {self._speed}, State: {self.machine.state}.")
        logging.info(f"EV info (Cont'd): Start time: {self.start_time},  soc usage threshold: {self._soc_usage_thresh}, range anxiety {self.range_anxiety}.")
        logging.info(f"EV Grid info: current position: {self.pos}, destination position: {self.dest_pos}, Distance goal: {self._distance_goal}.")        
        logging.info(f"Location info: current location (LSM): {self.loc_machine.state}, source: {self.source}, destination: {self.destination}, route: {self.route}.")

    # Internal functions
    def set_source_loc_mac_from_source(self, source:str) -> None:
        """Sets the EV's location machine state to the initial location on arrival."""
        self.loc_machine.set_state(source)

    def update_loc_mac_with_destination(self, destination:str) -> None:
        """Updates the EV's location machine state to the destination on arrival.
        Args:
            destination (str): The destination of the EV's journey.
        """
        self.loc_machine.set_state(destination)
    
    def get_initial_location_from_route(self, route:str) -> str:
        """
        Extracts and returns the location of the EV from its assigned route.

        Args:
            route (str): The route of the EV's journey.
        Returns:
            initial_location (str): The start location of the EV's journey.
        """
        initial_location = worker.get_string_before_hyphen(route) 
        self.source = initial_location                                           # TO-DO separate get and set
        return initial_location

    def get_destination_from_route(self, route:str) -> str:
        """
        Extracts and returns the destination of the EV from its assigned route.
        Sets the EV's destination to the destination of the assigned route.
        Args:
            route (str): The route of the EV's journey.
        Returns:        
            destination (str): The destination of the EV's journey.

        """
        destination = worker.get_string_after_hyphen(route)
        self.destination = destination                                           # TO-DO  separate get and set
        return destination
    
    def update_destination_for_new_trip(self, location:str) -> str:
        """
        Updates the EV's destination for a new trip.
        """
        options = worker.get_possible_journeys_long(location)
        return random.choice(options)
    
    def set_speed(self) -> None:
        """Sets the speed of the EV."""
        base_speed = 20 # km/h. Was 10
        self._speed = base_speed
    
    def set_ev_consumption_rate(self) -> None:
        """Sets the EV's energy consumption rate. in kWh/km.
        """
        # baselines
        mu =  0.5 # mean of distribution. Tried 1. Initially, set to 0.5 kWh/km
        sigma = 0.1 # standard deviation of distribution.
        # set vehicle energy consumption rate
        self.ev_consumption_rate = np.random.default_rng().normal(mu, sigma) # opt: size = 1

    def energy_usage_trip(self) -> float:
        """Energy consumption (EC) for the entire trip. EC is the product of distance covered and energy consumption rate.
        
        Returns:
            usage: Energy consumption for the entire trip.
        """
        usage = (self.ev_consumption_rate * self.odometer)
        return usage

    def energy_usage_tick(self) -> float:
        """Energy consumption (EC) for each tick. EC is the product of distance covered and energy consumption rate per timestep (tick).
        
        Returns:
            usage: Energy consumption for each tick.
        """
        usage = (self.ev_consumption_rate * self._speed)
        # usage = (self.ev_consumption_rate * self.distance_margin)
        return usage

    def delta_battery_neg(self) -> float:
        """ Marginal negative change in battery level per tick.
        
        Returns:
            delta: Marginal negative change in battery level per tick.
        """
        delta = (self.tick_energy_usage / self.max_battery)
        return delta
    
    # interventions 
    def dead_intervention(self, model) -> None:
        """
        Intervention for when the EV runs out of battery. The EV is recharged to the maximum by emergency services and will be transported to its destination.
        """
        self.battery = self.max_battery
        self.increase_range_anxiety()
        self.machine.emergency_intervention()
        self.transport_ev_to_destination(model)
        # print(f"\nEV {self.unique_id} has been removed from the grid, recharged to {self.battery} by emergency services and is now in state: {self.machine.state}. Range anxiety has increased to: {self.range_anxiety}.")
        logging.info(f"\nEV {self.unique_id} has been removed from the grid, recharged to {self.battery} by emergency services and is now in state: {self.machine.state}. Range anxiety has increased to: {self.range_anxiety}.")
        # transport EV back to random location. source?

    def travel_intervention(self,model) -> None:
        """Intervention for when the EV is travelling. The EV is set to Idle and will be transported to its destination.
        """
        self.machine.end_travel()
        self.transport_ev_to_destination(model)
        # print(f"EV {self.unique_id} was forced to end its trip due to overrun. It is now in state: {self.machine.state}.")
        logging.info(f"EV {self.unique_id} was forced to end its trip due to overrun. It is now in state: {self.machine.state}.")
    
    def charge_intervention(self,model) -> None:
        """Intervention for when the EV is at a Charge Station. The EV is set to Idle and will be transported to its destination.
        """
        if self.machine.state == "Charge":
            self.machine.end_charge_abrupt()
        elif self.machine.state == "In_queue":
            self.machine.end_queue_abrupt()
        elif self.machine.state == "Seek_queue":
            self.machine.end_seek_queue_abrupt()
        self.transport_ev_to_destination(model)
        self._chosen_cs = None

        # print(f"EV {self.unique_id} was forced to end its charge due to time overrun. It is now in state: {self.machine.state}.")
        logging.info(f"EV {self.unique_id} was forced to end its charge due to time overrun. It is now in state: {self.machine.state}.")

    # def charge_intervention(self,model) -> None:
    #     """Intervention for when the EV is at a Charge Station. The EV is set to Idle and will be transported to its destination.
    #     """
    #     if self.machine.state == "Charge":
    #         self.machine.end_charge_abrupt()
    #     elif self.machine.state == "In_queue":
    #         self.machine.end_queue_abrupt()
    #     elif self.machine.state == "Seek_queue":
    #         self.machine.end_seek_queue_abrupt()
    #     self.transport_ev_to_destination(model)
    #     self._chosen_cs = None
        
    #     print(f"EV {self.unique_id} was forced to end its charge due to time overrun. It is now in state: {self.machine.state}.")
    
    def transport_ev_to_destination(self, model) -> None:
        """Transport the EV to its destination."""
        model.grid.remove_agent(self)
        model.grid.place_agent(self, self.dest_pos)
        self.pos = self.dest_pos
        # print(f"EV {self.unique_id} has been transported to Location {self.destination}. Coord: {self.pos}. State: {self.machine.state}.")
        logging.info(f"EV {self.unique_id} has been transported to Location {self.destination}. Coord: {self.pos}. State: {self.machine.state}.")
        # set location machine state to destination. Use loc_machine.transition instead?
        self.loc_machine.set_state(f"{self.destination}")
        # self.select_initial_coord(model)

    def set_start_time(self) -> None:
        """Sets the start time for the EV to travel. Sets start time based on distance goal - if distance goal is greater than or equal to 90 miles, start time is earlier.
        """
        if self._distance_goal < 90:
            self.start_time = random.randint(10, 14)

        elif self._distance_goal >= 90:
            self.start_time = random.randint(6, 9)

        if self.model.current_day_count > 0:
            self.start_time = (self.model.current_day_count * 24) + self.start_time
    
    # Range Anxiety charging behavior
    def increase_range_anxiety(self) -> None:
        """Increases the range anxiety (RA). Higher RA means that the EV is more likely to charge at a Charge Station, due to having a higher soc_usage threshold. """
        self.range_anxiety = max(min(self.range_anxiety + (abs(self.margin)), 1), 0)

    def decrease_range_anxiety(self) -> None:
        """Decreases the range anxiety (RA). Lower RA means that the EV is less likely to charge at a Charge Station, due to having a lower soc_usage threshold."""
        self.range_anxiety = max(min(self.range_anxiety - (abs(self.dec_margin)), 1), 0)
  
    # Core EV Functions
    def select_initial_coord(self, model) -> None:
        """Given model, selects the initial coordinates of the EV from the model's locations.
        
        Returns:
            coord: Initial coordinate for the EV.
        """
        try:
            self.pos = worker.get_location_coordinates_by_name(locations = model.location_params, location_name = self.source)

        except Exception as e:
            # print(f"Error selecting initial coordinates from 'source' variable: {e}")
            logging.warning(f"Error selecting initial coordinates from 'source' variable: {e}")
            # print(f"EV is trying to select initial coordinates for Location using 'current_location' {self.current_location}.")
            logging.info(f"EV is trying to select initial coordinates for Location using 'current_location' {self.current_location}.")
            self.pos = worker.get_location_coordinates_by_name(locations = model.location_params, location_name = self.current_location)
            # print(f"EV has selected initial coordinates for Location using 'current_location' {self.current_location}.")
            logging.info(f"EV has selected initial coordinates for Location using 'current_location' {self.current_location}.")

    def select_destination_coord(self,model) -> None:
        """Gets the destination of the EV.
        
        Returns:
            destination: Destination of the EV.
        """
        self.dest_pos = worker.get_location_coordinates_by_name(locations = model.location_params, location_name = self.destination)
        
    def get_distance_goal_and_coord_from_dest(self) -> tuple:
        """Calculates the distance to the destination from the EV's position and the coordinates of the destination."""
        # Calculate the unit vector towards the destination
        dx = self.dest_pos[0] - self.pos[0]
        dy = self.dest_pos[1] - self.pos[1]
        self._distance_goal = math.sqrt(dx*dx + dy*dy)
        # record initial distance goal. Reset at relaunch
        if self.static_distance_goal == 0: #from initalisation i.e active step one
            self.static_distance_goal = self._distance_goal
        elif self.static_distance_goal != 0:
            self.static_distance_goal = self.static_distance_goal
        # self.margin = self.static_goal
        return dx, dy, self._distance_goal

    def move(self, model) -> None:
        """Moves the EV towards its destination."""
        scaling_factor = 1 # np.sqrt(2)                                           # helps visuals map to underlying numbers.
        distance = self._distance_goal
        if distance == 0:
            # The EV has reached its destination
            self.dest_pos = None
            print(f"EV {self.unique_id} has reached its destination. IN MOVE")
            return
        
        dx,dy,distance = self.get_distance_goal_and_coord_from_dest()
 
        # Normalize the vector to get a unit vector
        dx /= distance
        dy /= distance
        
        scaled_x = dx * self._speed * scaling_factor
        scaled_y = dy * self._speed * scaling_factor
        
        # Calculate the next position of the EV by moving along the unit vector
        next_pos = (int((self.pos[0] + scaled_x)), int((self.pos[1] + scaled_y)))
        
        # Check if the next position is inside the grid boundaries
        if (0 <= next_pos[0] < model.grid.width) and (0 <= next_pos[1] < model.grid.height):
            # Move the EV to the next position
            model.grid.move_agent(self, next_pos)

        self.distance_margin = math.sqrt((scaled_x*scaled_x) + (scaled_y*scaled_y))
        # print(f"Step distance: {self.distance_margin}")
    
    
    def travel(self) -> None:
        """
        Travel function. Moves EV along the road. Updates odometer and battery level.
        
        Returns:
            odometer: Odometer reading for the EV.
            battery: Battery level for the EV.
        """
        self.move(self.model)
        # self.odometer += self._speed
        self.odometer += self.distance_margin
        # self.battery -= self.energy_usage_tick()
        self.battery = max(min(self.battery - self.energy_usage_tick(), self.max_battery), 0)

        self.calculate_soc()
        # print(f"EV {self.unique_id} is travelling. State: {self.machine.state}, Odometer: {self.odometer:.2f}, SOC: {self.soc:.1f}%, Battery: {self.battery:.2f}, Location: {self.pos}, Destination: {self.destination})")
        # print(f"Total distance: {self.static_distance_goal:.2f}, Distance covered in timestep: {self.distance_margin}, New distance goal: {self._distance_goal:.2f}.")
        logging.info(f"EV {self.unique_id} is travelling. State: {self.machine.state}, Odometer: {self.odometer:.2f}, SOC: {self.soc:.1f}%, Battery: {self.battery:.2f}, Location: {self.pos}, Destination: {self.destination})")
        logging.info(f"Total distance: {self.static_distance_goal:.2f}, Distance covered in timestep: {self.distance_margin}, New distance goal: {self._distance_goal:.2f}.")
        
        self.distance_margin = 0

        # use station selection process instead
    def search_for_charge_station(self, model) -> None:
        """EV in 'Travel_low' checks for Chargestations in neighbourhood."""
        neighbours = model.grid.get_neighbors(self.pos, moore=True, radius = 3, include_center=True)
        for neighbour in neighbours:
            if isinstance(neighbour, ChargeStation):
                self._chosen_cs = neighbour
                # print(f"EV {self.unique_id} has arrived at Charge Station {self._chosen_cs.name}.")
                logging.info(f"EV {self.unique_id} has arrived at Charge Station {self._chosen_cs.name}.")
                self.join_cs_queue()
                self._chosen_cs.location_occupancy += 1
                self._chosen_cs.location_occupancy_list.append(self.unique_id)
                # print(f"EV {self.unique_id} has joined the queue {self._chosen_cs.name}. Current CS occupancy: {self._chosen_cs.location_occupancy}")
                logging.info(f"EV {self.unique_id} has joined the queue {self._chosen_cs.name}. Current CS occupancy: {self._chosen_cs.location_occupancy}")
                break

    def charge(self):
        """
        Charge the EV at the Charge Station at the charge point's charge rate.
        EV charge rate is set in chargepoint assignment loop in ChargeStation class, using data from the station data file.
        
        Returns:
            battery: Battery level for the EV.
        """
        self.battery = max(min(self.battery + self.charge_rate, self.max_battery), 0)

    def charge_overnight(self):
        """
        Charge the EV at the Home Charge Station, at the Home Charge Station's charge rate.
        
        Returns:
            battery: Battery level for the EV.
        """
        self.battery += self.home_cs_rate
        # print(f"EV {self.unique_id} is charging at Home CS. State: {self.machine.state}, SOC: {self.soc}, Battery: {self.battery}, Rate: {self.home_cs_rate}.")
        logging.info(f"EV {self.unique_id} is charging at Home CS. State: {self.machine.state}, SOC: {self.soc}, Battery: {self.battery}, Rate: {self.home_cs_rate}.")
    
    def join_cs_queue(self) -> None:
        """Join the queue at the chosen Charge Station."""
        self._chosen_cs.queue.append(self)
        self.machine.join_charge_queue()
        # print(f"EV {(self.unique_id)} joined queue at Charge Station. CS Name: {(self._chosen_cs.name)} UID: {(self._chosen_cs.unique_id)}")
  
    # Model env functions
    def add_soc_eod(self) -> None:
        """Adds the battery level at the end of the day to a list."""
        self.battery_eod.append(self.battery)
        # print(f"EV {self.unique_id} Battery level at end of day: {self.battery_eod[-1]}")
        logging.info(f"EV {self.unique_id} Battery level at end of day: {self.battery_eod[-1]}")

    def reset_odometer(self) -> None:
        """Resets the EV odometer to 0."""
        self.odometer = 0
    
    def reset_static_distance_goal(self) -> None:
        """Resets the static distance goal of the EV."""
        self.static_distance_goal = 0
    
    def relaunch_base(self,n) -> None:
        """
        Relaunches the EV at the end of the day. Sets the start time to the next day, and chooses a new journey type and destination. Finally, generates an initialization report.
        Also sets the _journey_complete flag to 'False'.
        Args:
            n (int): Day number.

        Returns:
            start_time: Start time for the EV. [imp]
        """
        self.set_start_time() 
        self._journey_complete = False

    def relaunch_travel(self, model)-> None:
        """
        Relaunches EVs still in the travel state at the end of the day. 
        Calls the travel_intervention method, followed by the relaunch_base method.
        """
        self.travel_intervention(model)
        self.relaunch_base(n = self.model.current_day_count)

    def relaunch_charge(self,model) -> None:
        """
        Relaunches charging EVs by calling the charge_intervention method, followed by the relaunch_base method.
        """
        self.charge_intervention(model)
        self.relaunch_base(n = self.model.current_day_count)

    def relaunch_dead(self,model) -> None:
        """
        Relaunches dead EVs by calling the dead_intervention method, followed by the relaunch_base method.
        """
        self.dead_intervention(model)
        self.relaunch_base(n = self.model.current_day_count)

    def relaunch_idle(self) -> None:
        """
        Relaunches idle EVs by calling the relaunch_base method.
        """
        self.relaunch_base(n = self.model.current_day_count) # type: ignore

    def start_travel(self) -> None:
        """
        Starts the EV travelling at the assigned start time.
        """
        if self.model.schedule.time == self.start_time:
            self.machine.start_travel()
            # print(f"EV {self.unique_id} started travelling at {self.start_time} and is in state: {self.machine.state}")
            logging.info(f"EV {self.unique_id} started travelling at {self.start_time} and is in state: {self.machine.state}")
    
    # Define a function to calculate the Euclidean distance between two points
    def euc_distance(self, x1, y1, x2, y2)-> float:
        """Calculates the Euclidean distance between two points."""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    def register_ev_arrival(self, model) -> None:
        """Registers EV arrival at Location."""
        neighbours = model.grid.get_neighbors(self.pos, moore=True, radius = 20, include_center=True)
        for neighbour in neighbours:
            if isinstance(neighbour, Location):
                if self.machine.state == 'Idle' and self._journey_complete == True:  
                    self.current_location = neighbour
                    self.current_location.location_occupancy += 1
                    self.current_location.location_occupancy_list.append(self.unique_id)
                    # self.pos = self.current_location.pos #new
                    print(f"EV {self.unique_id} has arrived at {self.current_location.name}. Current occupancy: {self.current_location.location_occupancy}")
                    self.model.grid.remove_agent(self)
                    # print(f"EV {self.unique_id} has been removed from grid on arrival at {self.current_location.name}. Current state: {self.machine.state}")
                    logging.info(f"EV {self.unique_id} has been removed from grid on arrival at {self.current_location.name}. Current state: {self.machine.state}")
                    break
    
    def calculate_soc(self) -> float:
        """Calculates the state of charge of the EV."""
        self.soc = (self.battery / self.max_battery) * 100
        return self.soc
    
    # # for 4 point dataset 
    # def update_lsm(self, route:str) -> None:
    #     """Updates the location state machine for the EV, using the route variable."""
    #     source = worker.get_string_after_hyphen(route)
    #     dest = worker.get_string_after_hyphen(route)
    #     if source == 'A':
    #         if dest == 'B':
    #             self.loc_machine.city_a_2_b()
    #         elif dest == 'C':
    #             self.loc_machine.city_a_2_c()
    #     elif source == 'B':
    #         if dest == 'A':
    #             self.loc_machine.city_b_2_a()
    #         elif dest == 'C':
    #             self.loc_machine.city_b_2_c()
    #         elif dest == 'D':
    #             self.loc_machine.city_b_2_d()
    #     elif source == 'C':
    #         if dest == 'A':
    #             self.loc_machine.city_c_2_a()
    #         elif dest == 'B':
    #             self.loc_machine.city_c_2_b()
    #         elif dest == 'D':
    #             self.loc_machine.city_c_2_d()
    #     elif source == 'D':
    #         if dest == 'A':
    #             self.loc_machine.city_d_2_a()
    #         elif dest == 'B':
    #             self.loc_machine.city_d_2_b()
    #         elif dest == 'C':
    #             self.loc_machine.city_d_2_c()
       
    #     print(f"EV {self.unique_id} is at location (LSM): {self.loc_machine.state}")

    # TO-DO: must be dynamically created

    # for new data set. SouthEast England
    def update_lsm(self, route:str) -> None:
        """Updates the location state machine for the EV, using the route variable."""
        source = worker.get_string_after_hyphen(route)
        dest = worker.get_string_after_hyphen(route)
        if source == 'A':
            if dest == 'B':
                self.loc_machine.city_a_2_b()
            elif dest == 'F':
                self.loc_machine.city_a_2_f()
        elif source == 'B':
            if dest == 'A':
                self.loc_machine.city_b_2_a()
            elif dest == 'C':
                self.loc_machine.city_b_2_c()
        elif source == 'C':
            if dest == 'B':
                self.loc_machine.city_c_2_b()
            elif dest == 'D':
                self.loc_machine.city_c_2_d()
        elif source == 'D':
            if dest == 'C':
                self.loc_machine.city_d_2_c()
            elif dest == 'E':
                self.loc_machine.city_d_2_e()
            elif dest == 'F':
                self.loc_machine.city_d_2_f()
        elif source == 'E':
            if dest == 'D':
                self.loc_machine.city_e_2_d()
            elif dest == 'F':
                self.loc_machine.city_e_2_f()
        elif source == 'F':
            if dest == 'D':
                self.loc_machine.city_f_2_d()
            elif dest == 'A':
                self.loc_machine.city_f_2_a()
        # print(f"EV {self.unique_id} is at location (LSM): {self.loc_machine.state}")
        logging.info(f"EV {self.unique_id} is at location (LSM): {self.loc_machine.state}")

    # staged step functions
    def stage_1(self):
        """Stage 1: EV travels until it reaches the distance goal or runs out of battery. 
        If it needs to charge during the journey, it will execute he necessary actions in Stage 2.
        """
        # Transition Case 1: Start travelling. idle -> travel. EV will start travelling at the assigned start time.
        # if self.machine.state == 'Idle':
        if self.machine.state == 'Idle' and self._journey_complete == False:
            self.start_travel() 
  
        # Transition Case 3: Still travelling. Travel -> Travel
        # Transition Case 4: Still travelling, battery low. Travel -> Travel_low
        # Transition Case 5: Still travelling, battery dies. Travel_low -> Battery_dead
        
        if (self.machine.state == 'Travel' or self.machine.state == 'Travel_low'): #and (self.odometer < self.static_distance_goal):
        # if (self.machine.state == 'Travel' or self.machine.state == 'Travel_low') and (self.pos != self.dest_pos):
            if self.machine.state == 'Travel':
                self.travel()
                self.machine.continue_travel()
                # # Transition Case 2: Still travelling, battery low. Travel -> travel_low  
                if self.battery <= self._soc_usage_thresh:
                    self.machine.get_low()
                    # print(f"EV: {self.unique_id} has travelled: {self.odometer} km and is now running out of power. State: {self.machine.state}. SOC: {self.soc:.2f}%. Battery: {self.battery:.2f} kwh.")
                    logging.info(f"EV: {self.unique_id} has travelled: {self.odometer} km and is now running out of power. State: {self.machine.state}. SOC: {self.soc:.2f}%. Battery: {self.battery:.2f} kwh.")
            elif self.machine.state == 'Travel_low':
                # TO-DO: consider tweaking conditional below to compare battery level to energy usage per tick. Minimum 'allowed' battery level for travel.
                if self.battery > self.energy_usage_tick():
                # if self.battery > 0:
                    self.travel()
                    self.machine.continue_travel_low()
                    # print(f"EV {self.unique_id} is still travelling, but is low on charge and is seeking a charge station. SOC: {self.soc:.2f}%. Current charge: {self.battery:.2f} kWh.")
                    logging.info(f"EV {self.unique_id} is still travelling, but is low on charge and is seeking a charge station. SOC: {self.soc:.2f}%. Current charge: {self.battery:.2f} kWh.")


                elif self.battery < self.energy_usage_tick():
                    self.machine.deplete_battery()
                    self._journey_complete = True
                    # print(f"EV {self.unique_id} is out of charge and can no longer travel. State: {self.machine.state}. Current charge: {self.battery} kWh.")
                    logging.info(f"EV {self.unique_id} is out of charge and can no longer travel. State: {self.machine.state}. Current charge: {self.battery} kWh.")

    def stage_2(self):
        """Stage 2:
        Interaction with the Charge Station.
        - EVs will search for a charge station if they are low on charge.
        - EVs will charge at the station until they reach the charge threshold.

        
        """
        # Search for a charge station if the EV is low on charge.
        if self.machine.state == 'Travel_low':
            self.search_for_charge_station(self.model)
        
        # EV is at a charge station and charging.
        if self.machine.state == 'Charge':
            self._in_queue = False
            self._is_charging = True
            self.charge()
            # print(f"EV {self.unique_id} is charging. EV State: {self.machine.state}. Current charge: {self.battery} kWh")
            
            # Transition Case 6: EV is at a charge station and charging. Charge -> Travel
            # Duplicated in CS class. Consider removing permanently.
            
       # Transition Case 8: EV is at a Home charge point and charging. Idle -> Home_charge
       # Overnight charging governed at model level
        if self.machine.state == 'Home_charge':
            if self.battery >= self._soc_charging_thresh:   
                self.machine.end_home_charge()
                self._is_charging = False
                # print(f"EV {self.unique_id} has finished Home charging. EV State: {self.machine.state}. Current charge: {self.battery} kWh")
                logging.info(f"EV {self.unique_id} has finished Home charging. EV State: {self.machine.state}. Current charge: {self.battery} kWh")
            elif self.battery < self._soc_charging_thresh:
                self.machine.continue_home_charge()
                self.charge_overnight()
                # print(f"EV {self.unique_id} is still charging at home. EV State: {self.machine.state}, SOC: {self.soc}, current charge: {self.battery} kWh")
                logging.info(f"EV {self.unique_id} is still charging at home. EV State: {self.machine.state}, SOC: {self.soc}, current charge: {self.battery} kWh")
            elif self.model.schedule.time == (self.start_time-1):
                self.machine.end_home_charge()
                self._is_charging = False
                # print(f"EV {self.unique_id}'s trip begins in the next timestep. EV ended Home charging. EV State: {self.machine.state}. Current charge: {self.battery} kWh")
                logging.info(f"EV {self.unique_id}'s trip begins in the next timestep. EV ended Home charging. EV State: {self.machine.state}. Current charge: {self.battery} kWh")
        
        # # Transition Case 9: Journey Complete. travel -> idle
        if (self.machine.state == 'Travel') and self.odometer >= self.static_distance_goal:
            self.machine.end_travel()
            self._journey_complete = True
            self.decrease_range_anxiety()
            # update LSM state
            self.update_loc_mac_with_destination(self.destination)
            self.calculate_soc()
            # print(f"EV {self.unique_id} has completed its journey to Location {self.destination}. State: {self.machine.state}. This EV has travelled: {self.odometer} miles. SOC: {self.soc:.2f}%, Battery: {self.battery:.2f} kWh. Range anxiety: {self.range_anxiety:.2f}.")
            # print(f"EV Location (LSM): {self.loc_machine.state}")
            logging.info(f"EV {self.unique_id} has completed its journey to Location {self.destination}. State: {self.machine.state}. This EV has travelled: {self.odometer} miles. SOC: {self.soc:.2f}%, Battery: {self.battery:.2f} kWh. Range anxiety: {self.range_anxiety:.2f}.")
            logging.info(f"EV Location (LSM): {self.loc_machine.state}")
            self.register_ev_arrival(self.model)
            # print(f"EV {self.unique_id} has been removed from the grid. State: {self.machine.state}. This EV has travelled: {self.odometer} miles. Battery: {self.battery} kWh. Range anxiety: {self.range_anxiety}")
        
        # Transition Case 10: Journey complete, battery low. travel_low -> idle
        if (self.machine.state == 'Travel_low') and self.odometer >= self.static_distance_goal:
            self.machine.end_travel_low()
            self._journey_complete = True
            # decrease range anxiety
            self.decrease_range_anxiety()
            # update LSM state
            self.update_loc_mac_with_destination(self.destination)
            self.calculate_soc()
            # print(f"EV {self.unique_id} narrowly completed its journey to Location {self.destination}. State: {self.machine.state}. This EV has travelled: {self.odometer} miles. SOC: {self.soc:.2f}%, Battery: {self.battery:.2f} kWh. Range anxiety: {self.range_anxiety:.2f}.")
            # print(f"EV Location (LSM): {self.loc_machine.state}")
            logging.info(f"EV {self.unique_id} narrowly completed its journey to Location {self.destination}. State: {self.machine.state}. This EV has travelled: {self.odometer} miles. SOC: {self.soc:.2f}%, Battery: {self.battery:.2f} kWh. Range anxiety: {self.range_anxiety:.2f}.")
            logging.info(f"EV Location (LSM): {self.loc_machine.state}")
            self.register_ev_arrival(self.model)

class Location(Agent):
    """A location agent. This agent represents a location in the model, and is used to store information about the location.
    Expands in future revisions to serve as base class for specialised location types. 
    
    Attributes:
        location_type (str): The type of location. Can be 'Home', 'Work', 'Charge', 'Other'. 
        name (str): The name of the location.
        location_occupancy (int): The number of EVs currently at the location.
        location_occupancy_list (list): A list of EVs currently at the location. EV UIDs are stored in this list.

    Methods:
        check_location_for_arrivals: Checks the location for arrivals.
        ev_departure: Removes an EV from the location.
        stage_1: Stage 1 of the Location agent's behaviour.
        stage_2: Stage 2 of the Location agent's behaviour.
    
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.location_type = None
        self.name = None
        # self.location_capacity = 0
        self.x = None
        self.y = None
        self.pos = None
        self.location_occupancy = 0
        self.location_occupancy_list = []

    def check_location_for_arrivals(self, model):
        """Checks the location for arrivals."""
        neighbours = model.grid.get_neighbors(self.pos, moore=True, radius = 3, include_center=True)
        for neighbour in neighbours:
            if isinstance(neighbour, EV):
                if neighbour.machine.state == 'Idle' and neighbour._journey_complete == True:  
                # if (neighbour.machine.state == 'Travel' or neighbour.machine.state == 'Travel_low') and neighbour._journey_complete == True:  
                    self.location_occupancy += 1
                    self.location_occupancy_list.append(neighbour.unique_id)
                    # print(f"EV {neighbour.unique_id} has arrived at {self.name}. Current occupancy: {self.location_occupancy}")
                    logging.info(f"EV {neighbour.unique_id} has arrived at {self.name}. Current occupancy: {self.location_occupancy}")
                    model.grid.remove_agent(neighbour)
                    # print(f"EV {neighbour.unique_id} has been removed from grid on arrival at {self.name}. Current state: {neighbour.machine.state}")
                    logging.info(f"EV {neighbour.unique_id} has been removed from grid on arrival at {self.name}. Current state: {neighbour.machine.state}")
                    break
    
    def ev_departure(self):
        """Removes an EV from the location's occupancy list."""
        for ev_id in self.location_occupancy_list:
            ev = self.model.schedule.agents[ev_id]
            # if (ev.machine.state == 'Travel' or ev.machine.state == 'Travel_low') and ev._journey_complete == False:
            # if (ev.machine.state == 'Idle') and ev._journey_complete == False:
            if ev.start_time == self.model.schedule.time:
                self.location_occupancy -= 1
                self.location_occupancy_list.remove(ev_id)
                # print(f"EV {ev_id} has left {self.name}. Current occupancy: {self.location_occupancy}")
                logging.info(f"EV {ev_id} has left {self.name}. Current occupancy: {self.location_occupancy}")
                break 

    def stage_1(self):
        """Stage 1 of the location agent's step function."""
        # self.check_location_for_arrivals(self.model)

    def stage_2(self):
        """Stage 2 of the location agent's step function."""
        if self.location_occupancy_list != []:
            self.ev_departure()
