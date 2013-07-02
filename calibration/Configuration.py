'''
Created on Apr 2, 2013

@author: D3P988
'''
import re

# start big ugly .m copy/paste - about 3329 lines

#function [data] = Configuration(file_to_extract, classification)
def ConfigurationFunc(wdir, config_file, file_to_extract=None, classification=None):
	data = {}
	# This file contains data particular to each feeder, and regionalization data for each load classification being used. This data may be different for each feeder. 
	if file_to_extract == None:
		file_extracted = ''
	else:
		file_extracted = file_to_extract

	data["intro"] = 'Populated feeder '+ file_extracted +'.'
	
	if classification == None:
		classID = None
	else:
		classID = classification
		
	working_directory = re.sub('\\\\','\\\\\\\\',wdir)
	dir = working_directory+'\\\\schedules\\\\'
	data["directory"] = dir
	
	default_weather_by_region = { 	1:	['CA-San_francisco.tmy2', 	'PST+8PDT'],
									2:	['IL-Chicago.tmy2', 		'CST+6CDT'],
									3:	['AZ-Phoenix.tmy2', 		'MST+7MDT'],
									4:	['TN-Nashville.tmy2', 		'CST+6CDT'],
									5:	['FL-Miami.tmy2', 			'EST+5EDT'],
									6:	['HI-Honolulu.tmy2', 		'HST10'] }

	if file_to_extract == None:
		# Use default values.
		
		# Region Properties
		# - Weather File (May be .tmy2 or .csv)
		# - Region Identifier (1:West Coast (temperate), 2:North Central/Northeast (cold/cold), 3:Southwest (hot/arid), 4:Southeast/Central (hot/cold), 5:Southeast Coastal (hot/humid), 6: Hawaii (sub-tropical))
		# - Timezone
		
		# TODO: These variables should be filled in automatically, probably from 'make weather file' script. Within that function we should get the appropriate timestamp and region ID too. 
		data["weather"] = 'schedules\\\\SCADA_weather_ISW_gld.csv'
		data["timezone"] = 'PST+8PDT'
		region = 4
		
		if not region or region not in xrange(1,7):
			print ("No region ID found. Using region 1 (West Coast, Temperate) to fill in default house configurations.")
			region = 1
		data["region"] = region
		
		if "weather" not in data.keys() or not data["weather"]:
			print ("Using default weather file for climate region "+str(region))
			data["weather"] = 'schedules\\\\'+default_weather_by_region[region][0]
			data["timezone"] = default_weather_by_region[region][1]
		elif "timezone" not in data.keys() or not data["timezone"]:
			data["timezone"] = default_weather_by_region[region][1]

		# Feeder Properties
		# - Substation Rating in MVA (Additional 15% gives rated kW & pf = 0.87)
		# - Nominal Voltage of Feeder Trunk
		# - Secondary (Load Side) of Transformers
		# - Voltage Players Read Into Swing Node
		data["feeder_rating"] = 1.15*14.0
		data["nom_volt"] = 14400
		data["nom_volt2"] = 14400 #was set to 480 for taxonomy feeders
		data["load_shape_norm"] = None
		vA='schedules\\\\VA.player'
		vB='schedules\\\\VB.player'
		vC='schedules\\\\VC.player'
		data["voltage_players"] = ['"{:s}"'.format(vA),'"{:s}"'.format(vB),'"{:s}"'.format(vC)]
		
		# Voltage Regulation
		# - EOL Measurements (name of node, phases to measure (i.e. ['GC-12-47-1_node_7','ABC',1]))
		# - Voltage Regulationn ( [desired, min, max, high deadband, low deadband] )
		# - Regulators (list of names)
		# - Capacitor Outages ( [name of capacitor, outage player file])
		# - Peak Power of Feeder in kVA 
		data["EOL_points"] = []
		data["voltage_regulation"] = [14400, 12420, 15180, 60, 60]     
		data["regulators"] = []
		data["capacitor_outtage"] = []
		data["emissions_peak"] = 13910 # Peak in kVa base .85 pf of 29 (For emissions)
		
		# Time of Use (TOU)
		data["TOU_prices"] = [0.07590551, 0.15181102]
		data["TOU_hours"] = [12, 12, 6]
		data["TOU_stats"] = [0.11385826, 0.03795329]
		data["TOU_price_player"] = 'R1_1247_1_t0_TOU.player'
		
		# Critical Peak Price (CPP) 
		data["CPP_prices"] = [0.06998667, 0.13997334, 0.69986670]
		data["CPP_stats"] = [0.10999954, 0.03795329]
		data["CPP_price_player"] = 'R1_1247_1_t0_CPP.player'
		data["CPP_flag"] = 'CPP_days_R1.player' # Specifies critical day
		
		# Load Classifications
		data["load_classifications"] = ['Residential1', 'Residential2', 'Residential3', 'Residential4', 'Residential5', 'Residential6', 'Commercial1', 'Commercial2', 'Commercial3']    

		# Industrial Loads
		# - For each classification, flag if you want loads populated using normalized load shape
		# 	from player files rather than with houses. You may include a
		# 	maximum value such that loads less than that size are populated with
		# 	houses, and loads greater are populated with loadshape from player. 
		# - Note that the option exists to print any classification as constant power scaled by players.. the term "industrial" is used loosely.
		data["indust_class"] = [[0,0],[0,0],[0,0],[0,0],[0,0],[0,0],[0,0],[0,0],[0,0]]  #[(0 or 1), kW]
		data["loadshape_r"]='' # player file
		data["loadshape_i"]='' # player file
		data["loadshape"]=0+0j
		data["indust_scalar_com_r"]=0
		data["indust_scalar_com_i"]=0
		data["indust_scalar_com"]=0+0j

		# Thermal Percentages by Region
		# - The "columns" represent load classifications. The "rows" represent the breakdown within that classification of building age. 
		#   1:<1940     2:1980-89   3:<1940     4:1980-89   5:<1960     6:<1960     7:<2010 8:<2010 9:<2010
		#   1:1940-49   2:>1990     3:1940-49   4:>1990     5:1960-89   6:1960-89   7:-     8:-     9:-
		#   1:1950-59   2:-         3:1950-59   4:-         5:>1990     6:>1990     7:-     8:-     9:-
		#   1:1960-69   2:-         3:1960-69   4:-         5:-         6:-         7:-     8:-     9:-
		#   1:1970-79   2:-         3:1970-79   4:-         5:-         6:-         7:-     8:-     9:-
		#   1:-         2:-         3:-   		4:-         5:-         6:-         7:-     8:-     9:-
		
		# Using values from the old regionalization.m script. 
		# Retooled the old thermal percentages values into this new "matrix" form for classifications.
		if region == 1:
			thermal_percentages = [	[0.1652, 0.4935, 0.1652, 0.4935, 0.0000, 0.1940, 1, 1, 1],  #1
									[0.1486, 0.5064, 0.1486, 0.5064, 0.7535, 0.6664, 0, 0, 0], 	#2
									[0.2238, 0.0000, 0.2238, 0.0000, 0.2462, 0.1395, 0, 0, 0], 	#3
									[0.1780, 0.0000, 0.1780, 0.0000, 0.0000, 0.0000, 0, 0, 0], 	#4
									[0.2841, 0.0000, 0.2841, 0.0000, 0.0000, 0.0000, 0, 0, 0], 	#5
									[0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0, 0, 0]] 	#6 
			data["floor_area"] = [2209, 2209, 2209, 2209, 1054, 820, 0, 0, 0]
			data["one_story"] = [0.6887] * 9
			perc_gas = [0.7051] * 9 
			perc_pump = [0.0321] * 9
			perc_AC = [0.4348] * 9 
			wh_electric = [0.7455] * 9
			wh_size = [[0.0000,0.3333,0.6667]] * 9
			AC_type = [	[1, 1, 1, 1, 1, 1, 0, 0, 0], # central
						[0, 0, 0, 0, 0, 0, 0, 0, 0]] # window/wall unit
			over_sizing_factor = [	[ 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0, 0, 0], # central
									[ 0, 0, 0, 0, 0, 0, 0, 0, 0]] # window/wall unit
			perc_pool_pumps= [0.0904] * 9
		elif region == 2:
			thermal_percentages = [	[0.2873, 0.3268, 0.2873, 0.3268, 0.0000, 0.2878, 1, 1, 1],  #1
									[0.1281, 0.6731, 0.1281, 0.6731, 0.6480, 0.5308, 0, 0, 0], 	#2
									[0.2354, 0.0000, 0.2354, 0.0000, 0.3519, 0.1813, 0, 0, 0], 	#3
									[0.1772, 0.0000, 0.1772, 0.0000, 0.0000, 0.0000, 0, 0, 0], 	#4
									[0.1717, 0.0000, 0.1717, 0.0000, 0.0000, 0.0000, 0, 0, 0], 	#5
									[0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0, 0, 0]] 	#6 
			data["floor_area"] = [2951] * 9
			data["one_story"] = [0.5210] * 9
			perc_gas = [0.8927] * 9
			perc_pump = [0.0177] * 9
			perc_AC = [0.7528] * 9 
			wh_electric = [0.7485] * 9
			wh_size = [[0.1459,0.5836,0.2706]] * 9
			AC_type = [	[1, 1, 1, 1, 1, 1, 0, 0, 0], # central
						[0, 0, 0, 0, 0, 0, 0, 0, 0]] # window/wall unit
			over_sizing_factor = [	[ 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0, 0, 0], # central
									[ 0, 0, 0, 0, 0, 0, 0, 0, 0]] # window/wall unit
			perc_pool_pumps= [0.0591] * 9
		elif region == 3:
			thermal_percentages = [	[0.1240, 0.3529, 0.1240, 0.3529, 0.0000, 0.1079, 1, 1, 1],  #1
									[0.0697, 0.6470, 0.0697, 0.6470, 0.6343, 0.6316, 0, 0, 0], 	#2
									[0.2445, 0.0000, 0.2445, 0.0000, 0.3656, 0.2604, 0, 0, 0], 	#3
									[0.2334, 0.0000, 0.2334, 0.0000, 0.0000, 0.0000, 0, 0, 0], 	#4
									[0.3281, 0.0000, 0.3281, 0.0000, 0.0000, 0.0000, 0, 0, 0], 	#5
									[0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0, 0, 0]] 	#6 
			data["floor_area"] = [2370] * 9
			data["one_story"] = [0.7745] * 9
			perc_gas = [0.6723] * 9
			perc_pump = [0.0559] * 9
			perc_AC = [0.5259] * 9
			wh_electric = [0.6520] * 9
			wh_size = [[0.2072,0.5135,0.2793]] * 9
			AC_type = [	[1, 1, 1, 1, 1, 1, 0, 0, 0], # central
						[0, 0, 0, 0, 0, 0, 0, 0, 0]] # window/wall unit
			over_sizing_factor = [	[ 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0, 0, 0], # central
									[ 0, 0, 0, 0, 0, 0, 0, 0, 0]] # window/wall unit
			perc_pool_pumps= [0.0818] * 9
		elif region == 4:
			thermal_percentages = [	[0.1470, 0.3297, 0.1470, 0.3297, 0.0000, 0.1198, 1, 1, 1],  #1
									[0.0942, 0.6702, 0.0942, 0.6702, 0.5958, 0.6027, 0, 0, 0], 	#2
									[0.2253, 0.0000, 0.2253, 0.0000, 0.4041, 0.2773, 0, 0, 0], 	#3
									[0.2311, 0.0000, 0.2311, 0.0000, 0.0000, 0.0000, 0, 0, 0], 	#4
									[0.3022, 0.0000, 0.3022, 0.0000, 0.0000, 0.0000, 0, 0, 0], 	#5
									[0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0, 0, 0]] 	#6 
			data["floor_area"] = [2655] * 9
			data["one_story"] = [0.7043] * 9
			perc_gas = [0.4425] * 9
			perc_pump = [0.1983] * 9
			perc_AC = [0.9673] * 9
			wh_electric = [0.3572] * 9
			wh_size = [[0.2259,0.5267,0.2475]] * 9
			AC_type = [	[1, 1, 1, 1, 1, 1, 0, 0, 0], # central
						[0, 0, 0, 0, 0, 0, 0, 0, 0]] # window/wall unit
			over_sizing_factor = [	[ 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0, 0, 0], # central
									[ 0, 0, 0, 0, 0, 0, 0, 0, 0]] # window/wall unit
			perc_pool_pumps= [0.0657] * 9
		elif region == 5:
			thermal_percentages = [	[0.1470, 0.3297, 0.1470, 0.3297, 0.0000, 0.1198, 1, 1, 1],  #1
									[0.0942, 0.6702, 0.0942, 0.6702, 0.5958, 0.6027, 0, 0, 0], 	#2
									[0.2253, 0.0000, 0.2253, 0.0000, 0.4041, 0.2773, 0, 0, 0], 	#3
									[0.2311, 0.0000, 0.2311, 0.0000, 0.0000, 0.0000, 0, 0, 0], 	#4
									[0.3022, 0.0000, 0.3022, 0.0000, 0.0000, 0.0000, 0, 0, 0], 	#5
									[0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0, 0, 0]] 	#6 
			data["floor_area"] = [2655] * 9
			data["one_story"] = [0.7043] * 9
			perc_gas = [0.4425] * 9
			perc_pump = [0.1983] * 9
			perc_AC = [0.9673] * 9
			wh_electric = [0.3572] * 9
			wh_size = [[0.2259,0.5267,0.2475]] * 9
			AC_type = [	[1, 1, 1, 1, 1, 1, 0, 0, 0], # central
						[0, 0, 0, 0, 0, 0, 0, 0, 0]] # window/wall unit
			over_sizing_factor = [	[ 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0, 0, 0], # central
									[ 0, 0, 0, 0, 0, 0, 0, 0, 0]] # window/wall unit
			perc_pool_pumps= [0.0657] * 9
		elif region == 6:
			thermal_percentages = [	[0.2184, 0.3545, 0.2184, 0.3545, 0.0289, 0.2919, 1, 1, 1],  #1
									[0.0818, 0.6454, 0.0818, 0.6454, 0.6057, 0.5169, 0, 0, 0], 	#2
									[0.2390, 0.0000, 0.2390, 0.0000, 0.3652, 0.1911, 0, 0, 0], 	#3
									[0.2049, 0.0000, 0.2049, 0.0000, 0.0000, 0.0000, 0, 0, 0], 	#4
									[0.2556, 0.0000, 0.2556, 0.0000, 0.0000, 0.0000, 0, 0, 0], 	#5
									[0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0, 0, 0]] 	#6 
			data["floor_area"] = [2655] * 9
			data["one_story"] = [0.7043] * 9
			perc_gas = [0.4425] * 9
			perc_pump = [0.1983] * 9
			perc_AC = [0.9673] * 9
			wh_electric = [0.3572] * 9
			wh_size = [[0.2259,0.5267,0.2475]] * 9
			AC_type = [	[1, 1, 1, 1, 1, 1, 0, 0, 0], # central
						[0, 0, 0, 0, 0, 0, 0, 0, 0]] # window/wall unit
			over_sizing_factor = [	[ 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0, 0, 0], # central
									[ 0, 0, 0, 0, 0, 0, 0, 0, 0]] # window/wall unit
			perc_pool_pumps= [0.0657] * 9
			
			
		# Single-Family Homes
		# - Designate the percentage of SFH in each classification
		SFH = [[1, 1, 1, 1, 0, 0, 0, 0, 0], # Res1-Res4 are 100% SFH.
               [1, 1, 1, 1, 0, 0, 0, 0, 0],
               [1, 1, 1, 1, 0, 0, 0, 0, 0],
               [1, 1, 1, 1, 0, 0, 0, 0, 0],
               [1, 1, 1, 1, 0, 0, 0, 0, 0],
               [1, 1, 1, 1, 0, 0, 0, 0, 0]] 

		# Commercial Buildings
		# - Designate what type of commercial building each classification represents.
		com_buildings = [[0, 0, 0, 0, 0, 0, 0, 0, 1],  # office buildings 
                         [0, 0, 0, 0, 0, 0, 0, 1, 0],  # big box 
                         [0, 0, 0, 0, 0, 0, 1, 0, 0]]  # strip mall

		# COP High/Low Values
		# - "columns" represent load classifications. The "rows" represent the sub-classifications (See thermal_percentages).
		cop_high = [[2.8, 3.8, 2.8, 3.8, 0.0, 2.8, 0, 0, 0], 
                    [3.0, 4.0, 3.0, 4.0, 2.8, 3.0, 0, 0, 0], 
                    [3.2, 0.0, 3.2, 0.0, 3.5, 3.2, 0, 0, 0], 
                    [3.4, 0.0, 3.4, 0.0, 0.0, 0.0, 0, 0, 0], 
                    [3.6, 0.0, 3.6, 0.0, 0.0, 0.0, 0, 0, 0], 
                    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0]]
		
		cop_low = [[2.4, 3.0, 2.4, 3.0, 0.0, 1.9, 0, 0, 0], 
                   [2.5, 3.0, 2.5, 3.0, 1.9, 2.0, 0, 0, 0], 
                   [2.6, 0.0, 2.6, 0.0, 2.2, 2.1, 0, 0, 0], 
                   [2.8, 0.0, 2.8, 0.0, 0.0, 0.0, 0, 0, 0], 
                   [3.0, 0.0, 3.0, 0.0, 0.0, 0.0, 0, 0, 0], 
                   [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0]]

		# Thermal Properties
		# - There should be a list of properties for each entry in thermal_percentages. (Each sub-classification in each classification)
		# - thermal_properties[i][j] = [ R-ceil,R-wall,R-floor,window layers,window glass, glazing treatment, window frame, R-door, Air infiltrationS ]
		# - for i = subclassficaiton, j = classification
		thermal_properties = [None] * 6 
		for i in xrange(6):
			thermal_properties[i] = [None] * 9  
			# Now we have a list of 6 lists of "None"

		# For each non-zero entry for a classification ("column") in thermal_percentages, fill in thermal properties. 
		# Res 1 (sfh pre-1980, <2000sf)
		thermal_properties[0][0] = [16, 10, 10, 1, 1, 1, 1, 3, 0.75]  # <1940
		thermal_properties[1][0] = [19, 11, 12, 2, 1, 1, 1, 3, 0.75]  # 1940-49
		thermal_properties[2][0] = [19, 14, 16, 2, 1, 1, 1, 3, 0.50]  # 1950-59
		thermal_properties[3][0] = [30, 17, 19, 2, 1, 1, 2, 3, 0.50]  # 1960-69
		thermal_properties[4][0] = [34, 19, 20, 2, 1, 1, 2, 3, 0.50]  # 1970-79
		thermal_properties[5][0] = [0, 0, 0, 0, 0, 0, 0, 0, 0]        # n/a
		
		# Res2 (sfh post-1980, <2000sf)
		thermal_properties[0][1] = [36, 22, 22, 2, 2, 1, 2, 5, 0.25]  # 1980-89
		thermal_properties[1][1] = [48, 28, 30, 3, 2, 2, 4, 11, 0.25] # >1990
		thermal_properties[2][1] = [0, 0, 0, 0, 0, 0, 0, 0, 0]        # n/a
		thermal_properties[3][1] = [0, 0, 0, 0, 0, 0, 0, 0, 0]        # n/a
		thermal_properties[4][1] = [0, 0, 0, 0, 0, 0, 0, 0, 0]        # n/a
		thermal_properties[5][1] = [0, 0, 0, 0, 0, 0, 0, 0, 0]        # n/a
		
		# Res3 (sfh pre-1980, >2000sf, val's identical to Res1)
		thermal_properties[0][2] = [16, 10, 10, 1, 1, 1, 1, 3, 0.75]  # <1940
		thermal_properties[1][2] = [19, 11, 12, 2, 1, 1, 1, 3, 0.75]  # 1940-49
		thermal_properties[2][2] = [19, 14, 16, 2, 1, 1, 1, 3, 0.50]  # 1950-59
		thermal_properties[3][2] = [30, 17, 19, 2, 1, 1, 2, 3, 0.50]  # 1960-69
		thermal_properties[4][2] = [34, 19, 20, 2, 1, 1, 2, 3, 0.50]  # 1970-79
		thermal_properties[5][2] = [0, 0, 0, 0, 0, 0, 0, 0, 0]        # n/a
		
		# Res4 (sfh post-1980, >2000sf, val's identical to Res2)
		thermal_properties[0][3] = [36, 22, 22, 2, 2, 1, 2, 5, 0.25]  # 1980-89
		thermal_properties[1][3] = [48, 28, 30, 3, 2, 2, 4, 11, 0.25] # >1990
		thermal_properties[2][3] = [0, 0, 0, 0, 0, 0, 0, 0, 0]        # n/a
		thermal_properties[3][3] = [0, 0, 0, 0, 0, 0, 0, 0, 0]        # n/a
		thermal_properties[4][3] = [0, 0, 0, 0, 0, 0, 0, 0, 0]        # n/a
		thermal_properties[5][3] = [0, 0, 0, 0, 0, 0, 0, 0, 0]        # n/a
		
		# Res5 (mobile homes)
		thermal_properties[0][4] = [0, 0, 0, 0, 0, 0, 0, 0, 0]               # <1960
		thermal_properties[1][4] = [13.4, 9.2,  11.7, 1, 1, 1, 1, 2.2, .75]  # 1960-1989
		thermal_properties[2][4] = [24.1, 11.7, 18.1, 2, 2, 1, 2, 3.0, .75]  # >1990
		thermal_properties[3][4] = [0, 0, 0, 0, 0, 0, 0, 0, 0]               # n/a
		thermal_properties[4][4] = [0, 0, 0, 0, 0, 0, 0, 0, 0]               # n/a
		thermal_properties[5][4] = [0, 0, 0, 0, 0, 0, 0, 0, 0]               # n/a
		
		# Res6 (apartments)
		thermal_properties[0][5] = [13.4, 11.7,  9.4, 1, 1, 1, 1, 2.2, .75]    # <1960
		thermal_properties[1][5] = [20.3, 11.7, 12.7, 2, 1, 2, 2, 2.7, 0.25]   # 1960-1989
		thermal_properties[2][5] = [28.7, 14.3, 12.7, 2, 2, 3, 4, 6.3, 0.125]  # >1990 
		thermal_properties[3][5] = [0, 0, 0, 0, 0, 0, 0, 0, 0]                 # n/a
		thermal_properties[4][5] = [0, 0, 0, 0, 0, 0, 0, 0, 0]                 # n/a
		thermal_properties[5][5] = [0, 0, 0, 0, 0, 0, 0, 0, 0]                 # n/a
		
		# Com3
		thermal_properties[0][6] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		thermal_properties[1][6] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		thermal_properties[2][6] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		thermal_properties[3][6] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		thermal_properties[4][6] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		thermal_properties[5][6] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		
		# Com2
		thermal_properties[0][7] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		thermal_properties[1][7] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		thermal_properties[2][7] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		thermal_properties[3][7] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		thermal_properties[4][7] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		thermal_properties[5][7] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		
		# Com1
		thermal_properties[0][8] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		thermal_properties[1][8] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		thermal_properties[2][8] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		thermal_properties[3][8] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		thermal_properties[4][8] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		thermal_properties[5][8] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
		
		# Floor Area by Classification
		#data["floor_area"] = [1200, 1200, 2400, 2400, 1710, 820, 0, 0, 0]

		# Percentage One Story Homes by Classification
		#data["one_story"] = [0.6295, 0.5357, 0.6295, 0.5357, 1.0000, 0.9073, 0, 0, 0]
		
		# Cooling Setpoint Bins by Classification
		# [nighttime percentage, high bin value, low bin value]
		cooling_setpoint = [None] * 9
		
		cooling_setpoint[0] =  [[0.098, 69, 65], #Res1
                                [0.140, 70, 70],
                                [0.166, 73, 71],
                                [0.306, 76, 74],
                                [0.206, 79, 77],
                                [0.084, 85, 80]]
		
		cooling_setpoint[1] =  [[0.098, 69, 65], #Res2
                                [0.140, 70, 70],
                                [0.166, 73, 71],
                                [0.306, 76, 74],
                                [0.206, 79, 77],
                                [0.084, 85, 80]]
		
		cooling_setpoint[2] =  [[0.098, 69, 65], #Res3
                                [0.140, 70, 70],
                                [0.166, 73, 71],
                                [0.306, 76, 74],
                                [0.206, 79, 77],
                                [0.084, 85, 80]]
		
		cooling_setpoint[3] =  [[0.098, 69, 65], #Res4
                                [0.140, 70, 70],
                                [0.166, 73, 71],
                                [0.306, 76, 74],
                                [0.206, 79, 77],
                                [0.084, 85, 80]]
		
		cooling_setpoint[4] =  [[0.138, 69, 65], #Res5
                                [0.172, 70, 70],
                                [0.172, 73, 71],
                                [0.276, 76, 74],
                                [0.138, 79, 77],
                                [0.103, 85, 80]]
		
		cooling_setpoint[5] =  [[0.155, 69, 65], #Res6
                                [0.207, 70, 70],
                                [0.103, 73, 71],
                                [0.310, 76, 74],
                                [0.155, 79, 77],
                                [0.069, 85, 80]]
		
		cooling_setpoint[6] =  [[0.098, 69, 65], #Com1
                                [0.140, 70, 70],
                                [0.166, 73, 71],
                                [0.306, 76, 74],
                                [0.206, 79, 77],
                                [0.084, 85, 80]]
		
		cooling_setpoint[7] =  [[0.098, 69, 65], #Com2
                                [0.140, 70, 70],
                                [0.166, 73, 71],
                                [0.306, 76, 74],
                                [0.206, 79, 77],
                                [0.084, 85, 80]]
		
		cooling_setpoint[8] =  [[0.098, 69, 65], #Com3
                                [0.140, 70, 70],
                                [0.166, 73, 71],
                                [0.306, 76, 74],
                                [0.206, 79, 77],
                                [0.084, 85, 80]]

		# Heating Setpoint Bins by Classification
		heating_setpoint = [None] * 9
		
		heating_setpoint[0] =  [[0.141, 63, 59], #Res1
                                [0.204, 66, 64],
                                [0.231, 69, 67],
                                [0.163, 70, 70],
                                [0.120, 73, 71],
                                [0.141, 79, 74]]
		
		heating_setpoint[1] =  [[0.141, 63, 59], #Res2
                                [0.204, 66, 64],
                                [0.231, 69, 67],
                                [0.163, 70, 70],
                                [0.120, 73, 71],
                                [0.141, 79, 74]]
		
		heating_setpoint[2] =  [[0.141, 63, 59], #Res3
                                [0.204, 66, 64],
                                [0.231, 69, 67],
                                [0.163, 70, 70],
                                [0.120, 73, 71],
                                [0.141, 79, 74]]
		
		heating_setpoint[3] =  [[0.141, 63, 59], #Res4
                                [0.204, 66, 64],
                                [0.231, 69, 67],
                                [0.163, 70, 70],
                                [0.120, 73, 71],
                                [0.141, 79, 74]]
		
		heating_setpoint[4] =  [[0.129, 63, 59], #Res5
                                [0.177, 66, 64],
                                [0.161, 69, 67],
                                [0.274, 70, 70],
                                [0.081, 73, 71],
                                [0.177, 79, 74]]
		
		heating_setpoint[5] =  [[0.085, 63, 59], #Res6
                                [0.132, 66, 64],
                                [0.147, 69, 67],
                                [0.279, 70, 70],
                                [0.109, 73, 71],
                                [0.248, 79, 74]]
		
		heating_setpoint[6] =  [[0.141, 63, 59], #Com1
                                [0.204, 66, 64],
                                [0.231, 69, 67],
                                [0.163, 70, 70],
                                [0.120, 73, 71],
                                [0.141, 79, 74]]
		
		heating_setpoint[7] =  [[0.141, 63, 59], #Com2
                                [0.204, 66, 64],
                                [0.231, 69, 67],
                                [0.163, 70, 70],
                                [0.120, 73, 71],
                                [0.141, 79, 74]]
		
		heating_setpoint[8] =  [[0.141, 63, 59], #Com3
                                [0.204, 66, 64],
                                [0.231, 69, 67],
                                [0.163, 70, 70],
                                [0.120, 73, 71],
                                [0.141, 79, 74]]
		
		# Heating
		# - Percentage breakdown of heating system type by classification.
		#perc_gas     = [0.52, 0.36, 0.52, 0.36, 0.16, 0.33, 0, 0, 0] 
		
		#perc_pump    = [0.37, 0.57, 0.37, 0.57, 0.34, 0.53, 0, 0, 0]
		
		perc_res = list(map(lambda x, y:1-x-y, perc_pump, perc_gas))
		
		# Cooling
		# - Percentage AC
		# - Breakdown AC unit types([central AC; window/wall units])
		# - Oversizing factor of AC units by load classification and unit type (central/window wall)
		#perc_AC = [0.94, 1.00, 0.94, 1.00, 0.94, 0.93, 0, 0, 0] 
		
		# AC_type = [[0.90, 1.00, 0.90, 1.00, 0.88, 0.87, 0, 0, 0],
                   # [0.10, 0.00, 0.10, 0.00, 0.12, 0.13, 0, 0, 0]]
		
		# over_sizing_factor = [[ 0, 0, 0, 0, 0, 0, 0, 0, 0],
                              # [ 0, 0, 0, 0, 0, 0, 0, 0, 0]]
		
		# Percent Pool Pumps by Classification
		#perc_pool_pumps = [0, 0, 0, 0, 0, 0, 0, 0, 0]
		
		# Waterheater
		# - Percentage electric water heaters by classificaition
		# - Waterheater sizing breakdown  [<30, 31-49, >50] by classification
		#wh_electric = [0.67, 0.49, 0.67, 0.49, 0.73, 0.96, 0, 0, 0]
		
		# wh_size = [[0.2259,0.5267, 0.2475],  #Res1
                   # [0.2259, 0.5267, 0.2475], #Res2
                   # [0.2259, 0.5267, 0.2475], #Res3
                   # [0.2259, 0.5267, 0.2475], #Res4
                   # [0.2259, 0.5267, 0.2475], #Res5
                   # [0.2259, 0.5267, 0.2475], #Res6
                   # [0, 0, 0],                #Com1
                   # [0, 0, 0],                #Com2
                   # [0, 0, 0]]                #Com3
		
		# Additional Solar Modules
		# - penetration (%)
		# - solar rating (kVA)
		data["solar_penetration"] = 0.0
		data["solar_rating"] = 5
		
		# Existing Solar (modules in utility database)
		# - inverter object properties to be used
		# - solar module object properties to be used
		# if entry is blank (i.e. ''), default property value will be used in in the .glm:
		sol_inv_properties = ['', #1    # inverter_type (TWO_PULSE|SIX_PULSE|TWELVE_PULSE|PWM|FOUR_QUADRANT)
							  '', #2    # generator_status (ONLINE|OFFLINE)
							  '', #3    # generator_mode (UNKNOWN|CONSTANT_V|CONSTANT_PQ|CONSTANT_PF|SUPPLY_DRIVEN), 
										# -- default is CONSTANT_PF, and this property is irrelevent if inverter type is four quadrant:
							  '', #4    # V_In [V]
							  '', #5    # I_In [A]
							  '', #6    # four_quadrant_control_mode (NONE|CONSTANT_PQ|CONSTANT_PF)
										# -- this property is necessary only if inverter type is four quadrant:
							  '', #7    # P_Out [VA]  -- used for constant PQ mode
							  '', #8    # Q_Out [VAr] -- used for constant PQ mode
							  '', #9    # power_factor [pu] (used for constant pf mode)
							  '', #10   # rated_power [W]
							  '', #11   # use_multipoint_efficiency (TRUE|FALSE)
							  '', #12   # inverter_manufacturer (NONE|FRONIUS|SMA|XANTREX)
										#-- only used if multipoint efficiency:
							  '', #13   # maximum_dc_power [W] -- used if multipoint efficiency:
							  '', #14   # maximum_dc_voltage [V] -- used if multipoint effici ency:
							  '', #15   # minimum_dc_power [W] -- used if multipoint efficiency:
							  '', #16   # c_0 -- coefficient descibing the parabolic relationship between AC and DC power of the inverter
										#-- only used if multipoint efficiency:
							  '', #17   # c_1 -- coefficient allowing the maximum DC power to vary linearly with DC voltage
										#-- only used if multipoint efficiency:
							  '', #18   # c_2 -- coefficient allowing the minimum DC power to vary linearly with DC voltage
										#-- only used if multipoint efficiency:
							  ''] #19   # c_3 -- coefficient allowing c_0 to vary linearly with DC voltage
										#-- only used if multipoint efficiency:

		# properties of solar modules
		sol_module_properties = ['', 						#1	# generator_mode (SUPPLY_DRIVEN)
								 '', 						#2  # generator_status (ONLINE|OFFLINE)
								 'MULTI_CRYSTAL_SILICON', 	#3  # panel_type (SINGLE_CRYSTAL_SILICON|MULTI_CRYSTAL_SILICON|AMORPHOUS_SILICON|THIN_FILM_GA_AS|CONCENTRATOR)
								 '', 						#4  # NOCT [degF] --default is 118.4 degF, used to calculate Tmodule
								 '', 						#5  # Tmodule [degF] -- used to calculate Voc and VA_Out  
								 '', 						#6  # power_factor [pu] (used for constant pf mode)
								 '', 						#7  # Rated_Insolation [W/sf] -- default is 92.902
								 '', 						#8  # Pmax_temp_coeff -- used to calculate VA_Out, set by panel type selection if not set here:
								 '', 						#9  # Voc_temp_coeff -- used to calculate Voc, set by panel type selection if not set here:
								 '', 						#10 # V_Max [V] -- default is 27.1 + 0j, used to calculate V_Out
								 '', 						#11 # Voc_Max [V] -- default is 34 + 0j, used to calculate Voc and V_Out
								 '', 						#12 # efficiency [unit] -- set by panel type selection if not set here:
								 '', 						#13 # area [sf] -- default is 323 #TODO: should they be allowed to change this since it's figured out according to load size?
								 '', 						#14 # shading_factor -- default is 1 (no shading)
								 '20',  					#15 # tilt_angle -- default is 45 degrees
								 '', 						#16 # orientation_azimuth -- default is 0 (equator facing)
								 '', 						#17 # latitude_angle_fix (TRUE|FALSE) -- default is false (this fixes tilt angle to regions latitude as determined by the included climate info
								 'FIXED_AXIS'] 				#18 # orientation  (FIXED|DEFAULT) -- default is DEFAULT, which means tracking

		# what percentage breakdown of these configurations? (inverter with sol_inv_properties{n} will be parent to solar object with solar_module_properties{n})
		data["solar_inverter_config_breakdown"] = [1, #Res1
												   1, #Res2
												   1, #Res3
												   1, #Res4
												   1, #Res5
												   1, #Res6
												   1, #Com1
												   1, #Com2
												   1] #Com3

		## emission dispatch order
		# Nuc Hydro Solar BioMass Wind Coal NG GeoTherm Petro
		dispatch_order = [[1,5,2,3,4,7,6,8,9],   #Res1
						  [1,7,2,3,4,5,6,8,9],   #Res2
						  [1,7,2,3,4,5,6,8,9],   #Res3
						  [1,7,2,3,4,5,6,8,9],   #Res4
						  [1,7,2,3,4,6,5,8,9],   #Res5
						  [1,7,2,3,4,5,6,8,9],   #Res6
						  [1,7,2,3,4,5,6,8,9],   #Com1
						  [1,7,2,3,4,5,6,8,9],   #Com2
						  [1,7,2,3,4,6,5,8,9]]   #Com3
	else:
		# set dictionary values for basic configuration data for this feeder.
		pass
		
	if config_file==None:
		# set dictionary values (for default case)
		# Determines how many houses to populate (bigger avg_house = less houses)
		data["avg_house"] = 15000
		
		# Determines sizing of commercial loads (bigger avg_commercial = less houses)
		data["avg_commercial"] = 35000
		
		# Scale the responsive and unresponsive loads (percentage)
		data["base_load_scalar"] = 1
		
		# heating offset
		allsame_c = 2
		
		# cooling offset
		allsame_h = 2
		
		# COP high scalar
		COP_high = 1
		
		# COP low scalar
		COP_low = 1
		
		#variable to shift the residential schedule skew (seconds)
		data["residential_skew_shift"] = 0
		
		# decrease gas heating percentage
		decrease_gas = 1
		
		#TODO: this is actually in TechnologyParameters Right now...
		# widen schedule skew
		data["residential_skew_std"] = 2700
		
		# window wall ratio
		data["window_wall_ratio"] = 0.15
		
		# additional set point degrees
		data["addtl_heat_degrees"] = 0
		
		if 'feeder_load_shape_norm' in data.keys() and data['feeder_load_shape_norm'] is not None:
			# commercial zip fractions for loadshapes
			data["c_z_pf"] = 0.97
			data["c_i_pf"] = 0.97
			data["c_p_pf"] = 0.97
			data["c_zfrac"] = 0.2
			data["c_ifrac"] = 0.4
			data["c_pfrac"] = 1 - data["c_zfrac"] - data["c_ifrac"]
			
			# residential zip fractions for loadshapes
			data["r_z_pf"] = 0.97
			data["r_i_pf"] = 0.97
			data["r_p_pf"] = 0.97
			data["r_zfrac"] = 0.2
			data["r_ifrac"] = 0.4
			data["r_pfrac"] = 1 - data["r_zfrac"] - data["r_ifrac"]
		
	else:
		def num(s):
			try:
				return int(s)
			except ValueError:
				return float(s)
		
		couplets={}
		# open calibration file
		calib = open(config_file, 'r')
		# separate into lines
		lines = (calib.read()).split('\n')
		for l in lines:
			# ignore comment lines
			if re.match(r'^#',l) is None:
				# split at first comma
				f = l.split(',',1)
				if f[0] == 'all':
					couplets[f[0]]=f[1].split(',')
				else:
					# insert variable name and value into dictionary
					couplets[f[0]]=num(f[1])
		calib.close()
		data["avg_house"] = couplets['avg_house']

		data["avg_commercial"] = couplets['avg_comm']

		data["base_load_scalar"] = couplets['base_load_scalar'] + 1

		allsame_c = couplets['cooling_offset']

		allsame_h = couplets['heating_offset']

		COP_high = couplets['COP_high_scalar'] + 1

		COP_low = couplets['COP_low_scalar'] + 1

		data["residential_skew_shift"] = couplets['res_skew_shift']

		decrease_gas = 1 - couplets['decrease_gas']

		# widen schedule skew
		data["residential_skew_std"] = couplets['sched_skew_std']

		# window wall ratio
		data["window_wall_ratio"] = couplets['window_wall_ratio']

		# additional set point degrees
		data["addtl_heat_degrees"] = couplets['addtl_heat_degrees']
		
		if 'feeder_load_shape_norm' in data.keys() and data['feeder_load_shape_norm'] is not None:
			# commercial zip fractions for loadshapes
			data["c_z_pf"] = couplets["c_z_pf"]
			data["c_i_pf"] = couplets["c_i_pf"]
			data["c_p_pf"] = couplets["c_p_pf"]
			data["c_zfrac"] = couplets["c_zfrac"]
			data["c_ifrac"] = couplets["c_ifrac"]
			data["c_pfrac"] = 1 - data["c_zfrac"] - data["c_ifrac"]
			
			# residential zip fractions for loadshapes
			data["r_z_pf"] = couplets["r_z_pf"]
			data["r_i_pf"] = couplets["r_i_pf"]
			data["r_p_pf"] = couplets["r_p_pf"]
			data["r_zfrac"] = couplets["r_zfrac"]
			data["r_ifrac"] = couplets["r_ifrac"]
			data["r_pfrac"] = 1 - data["r_zfrac"] - data["r_ifrac"]
		
	# Apply calibration scalars
	for x in cooling_setpoint:
		if x is None:
			pass
		else:
			for j in xrange(len(x)):
				x[j].insert(1,allsame_c)
				
	for x in heating_setpoint:
		if x is None:
			pass
		else:
			for j in xrange(len(x)):
				x[j].insert(1,allsame_h)
				
	cop_high_new = []
	
	for x in cop_high:
		cop_high_new.append([round(COP_high*y,2) for y in x])
		
	cop_low_new = []
	
	for x in cop_low:
		cop_low_new.append([round(COP_low*y,2) for y in x])
		
	for i in xrange(len(thermal_properties)):
		if thermal_properties[i] is None:
			pass
		else:
			for j in xrange(len(thermal_properties[i])):
				if thermal_properties[i][j] is None:
					pass
				else:
					thermal_properties[i][j].extend([cop_high_new[i][j],cop_low_new[i][j]])
					
	perc_pump = list(map(lambda x, y: x + (1-decrease_gas)*y,perc_pump,perc_gas))
	perc_gas = list(map(lambda x:x*decrease_gas,perc_gas))
	
	#print("classification is = "+str(classID))

	#Variables referenced by Feeder_Generator.m
	if classification != None :
		data["thermal_percentages"] = [None]*len(thermal_percentages)
		for x in xrange(len(thermal_percentages)):
			data["thermal_percentages"][x] = thermal_percentages[x][classID]

		data["thermal_properties"] = [None]*len(thermal_properties)
		for x in xrange(len(thermal_properties)):
			data["thermal_properties"][x] = thermal_properties[x][classID]

		data["cooling_setpoint"] = cooling_setpoint[classID] 
		data["heating_setpoint"] = heating_setpoint[classID]
		data["perc_gas"] = perc_gas[classID]
		data["perc_pump"] = perc_pump[classID]
		data["perc_res"] = perc_res[classID]
		data["perc_AC"] = perc_AC[classID]
		data["perc_poolpumps"] = perc_pool_pumps[classID]
		data["wh_electric"] = wh_electric[classID]
		data["wh_size"] = wh_size[classID]
		
		data["over_sizing_factor"] = [None]*len(over_sizing_factor)
		for x in xrange(len(over_sizing_factor)):
			data["over_sizing_factor"][x] = over_sizing_factor[x][classID]
			
		data["AC_type"] = [None]*len(AC_type)
		for x in xrange(len(AC_type)):
			data["AC_type"][x] = AC_type[x][classID]
			
		data["dispatch_order"] = dispatch_order[classID]

		data["SFH"] = [None]*len(SFH)
		for x in xrange(len(SFH)):
			data["SFH"][x] = SFH[x][classID]


	data["sol_inv_properties"] = sol_inv_properties
	data["sol_module_properties"] = sol_module_properties
	data["com_buildings"] = com_buildings
	data["no_cool_sch"] = 8
	data["no_heat_sch"] = 6
	data["no_water_sch"] = 6
	data["ts_penetration"] = 10 #0-100, percent of buildings utilizing thermal storage - for all regions
	return data

def main():
	#tests here
	config_data = ConfigurationFunc(None,4)
	#print(config_data['cooling_setpoint'][0])
if __name__ ==  '__main__':
	main()
