# import worker
import csv


# Path Config
DATA_PATH = '/Users/ia329/Projects/ec4d/modeldata/'
CONFIG_PATH = '/Users/ia329/Projects/ec4d/config/'

# input file read-in functions
def read_csv(filename):
    """Reads a CSV file and returns a dictionary of dictionaries of dictionaries.
    The first key is the route, the second key is the station, the third key is the CPID.
    """
    data = {}
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            route = row['Route']
            station = row['Station']
            cpid = row['CPID']
            power = row['Power']
            distance = row['Distance']
            price = row['Price']
            green = row['Green']
            booking = row['Booking']
            if route not in data:
                data[route] = {}
            if station not in data[route]:
                data[route][station] = []
            data[route][station].append({
                'CPID': cpid,
                'Power': power,
                'Distance': distance,
                'Price': price,
                'Green': green,
                'Booking': booking
            })
    return data

def read_location_coords_from_csv(file_path):
    """Reads a CSV file and returns a dictionary of location names and coordinates."""
    location_dict = {}
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            location = row['location']
            x = int(row['x'])
            y = int(row['y'])
            location_dict[location] = (x, y)
    return location_dict

def get_location_coordinates_by_name(locations, location_name):
    """Returns the coordinates of a location by name."""
    return locations.get(location_name)

def read_location_names(file_path):
    """Reads a CSV file and returns a list of location names."""
    location_names = []
    with open(file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            location_names.append(row['location'])
    return location_names

# Model Parameterisation

# number of electric vehicles (EVs in the model
no_evs = 10
# number of timesteps or ticks in the model
ticks = 72
# 1 day = 24 ticks
# 3 days = 72 ticks
# 7 days = 168 ticks
# 30 days = 720 ticks
# 365_days = 8760 ticks

# # grid dimensions 
# grid_width = 100 #400 100
# grid_height = 100 #400 100
# canvas_height = 800
# canvas_width = 800

# # grid dimensions - f 
grid_width = 400 # 400
grid_height = 250 # 400 250
canvas_height = 750 #1200
canvas_width = 1200  #1200

# Station particulars - External file. Contains: price, green, booking
# station_config = read_csv(CONFIG_PATH +'stations.csv')
station_config = read_csv(CONFIG_PATH +'f_stations.csv')

# Location names (source/destination)- External file. Contains: names, coordinates.
# location_names = read_location_names(CONFIG_PATH +'locations.csv')
# location_config = read_location_coords_from_csv(CONFIG_PATH +'locations.csv')
location_names = read_location_names(CONFIG_PATH +'f_locations.csv')
location_config = read_location_coords_from_csv(CONFIG_PATH +'f_locations.csv')

# Station Coordinates
# station_location_config = read_location_coords_from_csv(CONFIG_PATH +'station_locations.csv')
station_location_config = read_location_coords_from_csv(CONFIG_PATH +'f_station_locations.csv')

# Overnight charging config - boolean
overnight_charging = False
# Logging - boolean
logging = False

# output data management: export_data - boolean, output_format - string
export_data = False
output_format = 'csv'



# new
