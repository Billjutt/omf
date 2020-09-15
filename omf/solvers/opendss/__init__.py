''' Run OpenDSS and plot the results for arbitrary circuits. '''

import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
import math
import os
import warnings
try:
	import opendssdirect as dss
except:
	warnings.warn('opendssdirect not installed; opendss functionality disabled.')

def runDSS(dssFilePath):
	''' Run DSS file and set export path. '''
	# Get paths because openDss doesn't like relative paths.
	fullPath = os.path.abspath(dssFilePath)
	dssFileLoc = os.path.dirname(fullPath)
	dss.run_command('Clear')
	dss.run_command('Redirect ' + fullPath)
	dss.run_command('Solve')
	# also generate coordinates.
	x = dss.run_command('Export BusCoords ' + dssFileLoc + '/coords.csv')
	coords = pd.read_csv(dssFileLoc + '/coords.csv', header=None)
	coords.columns = ['Element', 'X', 'Y']
	hyp = []
	for index, row in coords.iterrows():
		hyp.append(math.sqrt(row['X']**2 + row['Y']**2))
	coords['radius'] = hyp
	return coords

def voltagePlot(filePath, PU=True):
	''' Voltage plotting routine.'''
	dssFileLoc = os.path.dirname(os.path.abspath(filePath))
	volt_coord = runDSS(filePath)
	dss.run_command('Export voltages ' + dssFileLoc + '/volts.csv')
	# Generate voltage plots.
	voltage = pd.read_csv(dssFileLoc + '/volts.csv')
	volt_coord.columns = ['Bus', 'X', 'Y', 'radius']
	voltageDF = pd.merge(volt_coord, voltage, on='Bus') # Merge on the bus axis so that all data is in one frame.
	plt.title('Voltage Profile')
	plt.xlabel('Distance from source[miles]')
	if PU:
		for i in range(1, 4): 
			volt_ind = ' pu' + str(i)
			plt.scatter(voltageDF['radius'], voltageDF[volt_ind], label='Phase ' + str(i))
		plt.ylabel('Voltage [PU]')
		plt.legend()
		plt.savefig(dssFileLoc + '/Voltage Profile [PU].png')
	else:
		# plt.axis([1, 7, 2000, 3000]) # Ignore sourcebus-much greater-for overall magnitude.
		for i in range(1, 4): 
			mag_ind = ' Magnitude' + str(i)
			plt.scatter(voltageDF['radius'], voltageDF[mag_ind], label='Phase ' + str(i))
		plt.ylabel('Voltage [V]')
		plt.legend()
		plt.savefig(dssFileLoc + '/Voltage Profile [V].png')
	plt.clf()

def currentPlot(filePath):
	''' Current plotting function.'''
	dssFileLoc = os.path.dirname(os.path.abspath(filePath))
	curr_coord = runDSS(filePath)
	dss.run_command('Export currents ' + dssFileLoc + '/currents.csv')
	current = pd.read_csv(dssFileLoc + '/currents.csv')
	curr_coord.columns = ['Index', 'X', 'Y', 'radius'] # DSS buses don't have current, but are connected to it. 
	curr_hyp = []
	currentDF = pd.concat([curr_coord, current], axis=1)
	plt.xlabel('Distance from source [km]')
	plt.ylabel('Current [Amps]')
	plt.title('Current Profile')
	for i in range(1, 3):
		for j in range(1, 4):
			cur_ind = ' I' + str(i) + '_' + str(j)
			plt.scatter(currentDF['radius'], currentDF[cur_ind], label=cur_ind)
	plt.legend()
	plt.savefig(dssFileLoc + '/Current Profile.png')
	plt.clf()

def networkPlot(filePath):
	''' Plot the physical topology of the circuit. '''
	dssFileLoc = os.path.dirname(os.path.abspath(filePath))
	coords = runDSS(filePath)
	dss.run_command('Export voltages ' + dssFileLoc + '/volts.csv')
	volts = pd.read_csv(dssFileLoc + '/volts.csv')
	coords.columns = ['Bus', 'X', 'Y', 'radius']
	G = nx.Graph()
	# Get the coordinates.
	pos = {}
	for index, row in coords.iterrows():
		try:
			bus_name = str(int(row['Bus']))
		except:
			bus_name = row['Bus']
		G.add_node(bus_name)
		pos[bus_name] = (row['X'], row['Y'])
 	# Get the connecting edges using Pandas.
	lines = dss.utils.lines_to_dataframe()
	edges = []
	for index, row in lines.iterrows():
		#HACK: dss upercases everything in the outputs.
		bus1 = row['Bus1'][:4].upper().replace('.', '')
		bus2 = row['Bus2'][:4].upper().replace('.', '')
		edges.append((bus1, bus2))
	G.add_edges_from(edges)
	# We'll color the nodes according to voltage.
	volt_values = {}
	labels = {}
	for index, row in volts.iterrows():
		volt_values[row['Bus']] = row[' pu1']
		labels[row['Bus']] = row['Bus']
	colorCode = [volt_values.get(node, 0.0) for node in G.nodes()]
	# Start drawing.
	nodes = nx.draw_networkx_nodes(G, pos, node_color=colorCode)
	edges = nx.draw_networkx_edges(G, pos)
	nx.draw_networkx_labels(G, pos, labels, font_size=8)
	plt.colorbar(nodes)
	plt.xlabel('Distance [m]')
	plt.title('Network Voltage Layout')
	plt.savefig(dssFileLoc + '/networkPlot.png')
	plt.clf()

def THD(filePath):
	''' Calculate and plot total harmonic distortion. '''
	dssFileLoc = os.path.dirname(os.path.abspath(filePath))
	bus_coords = runDSS(filePath)
	dss.run_command('Solve mode=harmonics')
	dss.run_command('Export voltages ' + dssFileLoc + '/voltharmonics.csv')
	# Clean up temp file.
	try:
		base = os.path.basename(filePath)
		fnameMinusExt = os.path.splitext(base)[0]
		os.remove('{}_SavedVoltages.dbl'.format(fnameMinusExt))
	except:
		pass
	voltHarmonics = pd.read_csv(dssFileLoc + '/voltharmonics.csv')
	bus_coords.columns = ['Bus', 'X', 'Y', 'radius']
	voltHarmonics.columns.str.strip()
	for index, row in voltHarmonics.iterrows():
		voltHarmonics['THD'] = row[' Magnitude1']/(math.sqrt(row[' Magnitude2']**2 + row[' Magnitude3']**2))
	distortionDF = pd.merge(bus_coords, voltHarmonics, on='Bus') # Merge on the bus axis so that all data is in one frame.
	plt.scatter(distortionDF['radius'], distortionDF['THD'])
	plt.xlabel('Distance from Source [miles]')
	plt.ylabel('THD [Percentage]')
	plt.title('Total Harmonic Distortion')
	plt.savefig(dssFileLoc + '/THD.png')
	plt.clf()

def dynamicPlot(filePath, time_step, iterations):
	''' Do a dynamic, long-term study of the powerflow. time_step is in seconds. '''
	dssFileLoc = os.path.dirname(os.path.abspath(filePath))	
	runDSS(filePath)
	dss.run_command('Solve')
	dynamicCommand = 'Solve mode=dynamics stepsize=%d number=%d' % (time_step, iterations)
	dss.run_command(dynamicCommand)
	for i in range(iterations):
		voltString = 'Export voltages ' + dssFileLoc + '/dynamicVolt%d.csv' % i
		currentString = 'Export currents ' + dssFileLoc + '/dynamicCurrent%d.csv' % i
		dss.run_command(voltString)
		dss.run_command(currentString)
	powerData = []
	for j in range(iterations):
		curVolt = 'dynamicvolt%d.csv' % j
		curCurrent = 'dynamiccurrent%d.csv' % j
		voltProfile = pd.read_csv(dssFileLoc + '/' + curVolt)
		voltProfile.columns = voltProfile.columns.str.replace(' ', '')
		curProfile = pd.read_csv(dssFileLoc + '/' + curCurrent)
		curProfile.columns = curProfile.columns.str.replace(' ', '')
		sourceVoltage = voltProfile.loc[voltProfile['Bus'] == 'SOURCEBUS']
		sourceCurrent = curProfile.loc[curProfile['Element'] == 'Vsource.SOURCE']
		data_summary = {'Volts': (sourceVoltage['Magnitude1'], sourceVoltage['Magnitude2'], sourceVoltage['Magnitude3']), 
		'Currents': (sourceCurrent['I1_1'], sourceCurrent['I1_2'], sourceCurrent['I1_3'])}
		power_triplet = (data_summary['Volts'][0]*data_summary['Currents'][0], data_summary['Volts'][1]*data_summary['Currents'][1], data_summary['Volts'][2]*data_summary['Currents'][2])
		powerData.append(power_triplet)
	first_phase = [item[0] for item in powerData]
	second_phase = [item[1] for item in powerData]
	third_phase = [item[2] for item in powerData]
	plt.plot(first_phase, label='Phase one')
	plt.plot(second_phase, label='Phase two')
	plt.plot(third_phase, label='Phase three')
	plt.legend()
	plt.xlim(0, iterations-1)
	plt.xlabel('Time [s]')
	plt.ylabel('Power [kW]')
	plt.title('Dynamic Simulation Power Plot')
	plt.savefig(dssFileLoc + '/DynamicPowerPlot.png')
	os.system('rm ' + dssFileLoc + '/dynamicvolt* ' + dssFileLoc + '/dynamiccurrent*')

def faultPlot(filePath):
	''' Plot fault study. ''' 
	dssFileLoc = os.path.dirname(os.path.abspath(filePath))
	bus_coord = runDSS(filePath)
	dss.run_command('Solve Mode=FaultStudy')
	dss.run_command('Export fault ' + dssFileLoc + '/faults.csv')
	faultData = pd.read_csv(dssFileLoc + '/faults.csv')
	bus_coord.columns = ['Bus', 'X', 'Y', 'radius']
	faultDF = pd.concat([bus_coord, faultData], axis=1)
	faultDF.columns = faultDF.columns.str.strip()
	plt.axis([-1, 6, 0, 8000])
	plt.xlabel('Distance From Source [Miles]')
	plt.ylabel('Current [Amps]')
	plt.title('Fault Study')
	plt.scatter(faultDF['radius'], faultDF['3-Phase'], label='3-Phase to Ground')
	plt.scatter(faultDF['radius'], faultDF['1-Phase'], label='1-Phase to Ground')
	plt.scatter(faultDF['radius'], faultDF['L-L'], label='Line-to-Line')
	plt.legend()
	plt.savefig(dssFileLoc + '/Fault Currents.png')
	plt.clf()

def capacityPlot(filePath):
	''' Plot power vs. distance '''
	dssFileLoc = os.path.dirname(os.path.abspath(filePath))
	coords = runDSS(filePath)
	dss.run_command('Export Capacity ' + dssFileLoc + '/capacity.csv')
	capacityData = pd.read_csv(dssFileLoc + '/capacity.csv')
	coords.columns = ['Index', 'X', 'Y', 'radius']
	capacityDF = pd.concat([coords, capacityData], axis=1)
	fig, ax1 = plt.subplots()
	ax1.set_xlabel('Distance From Source [Miles]')
	ax1.set_ylabel('Power [kW]')
	ax1.scatter(capacityDF['radius'], capacityData[' kW'], label='Power')
	ax2 = ax1.twinx()
	ax2.set_ylabel('Maximum transformer percentage (One-side)')
	ax2.scatter(capacityDF['radius'], capacityDF.iloc[:, 2]+capacityDF.iloc[:, 3], label='Transformer Loading', color='red')
	fig.tight_layout() # otherwise the right y-label is slightly clipped
	fig.legend()
	plt.savefig(dssFileLoc + '/Capacity Profile.png')
	plt.clf()


def compareVoltsFiles(origFile, modFile):
	# Compares two of the files output by the 'Export voltages" opendss command. returns the maximum error encountered.
	if not ('.csv' in origFile and '.csv' in modFile):
		assert True, 'Input files must be .csv files of voltages output by OpenDss'
	ovolts = pd.read_csv(origFile, header=0)
	ovolts.index = ovolts['Bus']
	ovolts.drop(labels='Bus', axis=1, inplace=True)
	ovolts = ovolts.astype(float, copy=True)
	mvolts = pd.read_csv(modFile, header=0)
	mvolts.index = mvolts['Bus']
	mvolts.drop(labels='Bus', axis=1, inplace=True)
	mvolts = mvolts.astype(float, copy=True)
	cols = mvolts.columns
	resultErr = pd.DataFrame(index=mvolts.index, columns=cols)
	assert ovolts.size == mvolts.size, 'The matrices represented by the input files must have identical dimensions.'
	resultErr =  abs(ovolts - mvolts)/ovolts
	resultSumm = pd.DataFrame(index=['Max', 'Avg', 'Min'], columns=cols)
	for c in cols:
		resultSumm.loc['Max',c] = max(resultErr.loc[:,c])
		resultSumm.loc['Avg',c] = sum(resultErr.loc[:,c])/len(resultErr.loc[:,c])
		resultSumm.loc['Min',c] = min(resultErr.loc[:,c])
	maxErr = max(resultSumm.loc['Max',:])
	resultSumm.to_csv('volts_comparison_results.csv', header=True, index=True, mode='w')
	resultSumm = pd.DataFrame(index=[''],columns=cols)
	resultSumm.to_csv('volts_comparison_results.csv', header=False, index=True, mode='a')
	resultErr.to_csv('volts_comparison_results.csv', header=False, index=True, mode='a')
	return maxErr


def compareVoltsTrees(origTree, modTree):
	# Obtains and compares OpenDss voltage output for two .dss circuit files.
	# Inputs: relative path to two dss circuit definition files
	# Outputs: Maximum error encountered
	# TODO: Needs some path manipulation to be ready for production (i.e. pull needed files from omf\static)
	if not ('.dss' in origTree and '.dss' in modTree):
		assert True, 'Input files must be .dss circuit definition files.'
	voltagePlot(origTree) # outputs volts.csv
	os.rename('volts.csv','origVolts.csv')
	voltagePlot(modTree)
	os.rename('volts.csv','modVolts.csv')
	ovolts = pd.read_csv('origVolts.csv', header=0)
	os.remove('origVolts.csv')
	ovolts.index = ovolts['Bus']
	ovolts.drop(labels='Bus', axis=1, inplace=True)
	ovolts = ovolts.astype(float, copy=True)
	mvolts = pd.read_csv('modVolts.csv', header=0)
	os.remove('modVolts.csv')
	mvolts.index = mvolts['Bus']
	mvolts.drop(labels='Bus', axis=1, inplace=True)
	mvolts = mvolts.astype(float, copy=True)
	cols = mvolts.columns
	resultErr = pd.DataFrame(index=mvolts.index, columns=cols)
	assert ovolts.size == mvolts.size, 'The matrices represented by the input files must have identical dimensions.'
	resultErr =  abs(ovolts - mvolts)/ovolts
	resultSumm = pd.DataFrame(index=['Max', 'Avg', 'Min'], columns=cols)
	for c in cols:
		resultSumm.loc['Max',c] = max(resultErr.loc[:,c])
		resultSumm.loc['Avg',c] = sum(resultErr.loc[:,c])/len(resultErr.loc[:,c])
		resultSumm.loc['Min',c] = min(resultErr.loc[:,c])
	maxErr = max(resultSumm.loc['Max',:])
	resultSumm.to_csv('volts_comparison_results.csv', header=True, index=True, mode='w')
	resultSumm = pd.DataFrame(index=[''],columns=cols)
	resultSumm.to_csv('volts_comparison_results.csv', header=False, index=True, mode='a')
	resultErr.to_csv('volts_comparison_results.csv', header=False, index=True, mode='a')
	return maxErr



def _stripPhases(dssObjId): # (Is this even worth encapsulating?) YES.
	# expected input is a string of format <uniqueName> (or perhaps <dssObjectType>.<uniqueName> )
	dssObjId = dssObjId.split('.')
	if len(dssObjId) == 1:
		return dssObjId
	elif len(dssObjId) >= 2:
		return dssObjId[0]
	else:
		assert True, 'An unknown error occurred.' # this should never happen
		return dssObjId

def _mergeContigLinesOnce(tree): # TODO finish debugging this code block - LMS
	#Input: a list of dictionaries (TODO double-check that this is correct)
	# Create a lookup table of indices to object names for quick retrieval
	id2key = {tree[i].get('object', None):i for i,v in enumerate(tree)} # note that these are in the form <type>.<name> (no phase info)
	id2key.update({tree[i].get('bus', None):i for i,v in enumerate(tree) if tree[i].get('!CMD', None) == 'setbusxy'}) # form: <name>
	id2key.update({'t_' + tree[i].get('bus', None) + '_l':i for i,v in enumerate(tree) if tree[i].get('!CMD', None) == 'setbusxy'}) # form: <name>
	treecopy = tree.copy()
	removedids = []
	while treecopy:
		o = treecopy.pop() # destructively iterate through tree copy
		top = o
		# Get the top id and check that this is a line
		tid =  top.get('object', '')
		# Get bottom node (could be indicated by 'bus', 'bus1', 'bus2', or the first member of 'buses'. Must assume it will be appended with phase information)
		bid = ''
		for k in top.keys():
			if k == 'bus' or k == 'bus1': # not line-like #(remove?)
				continue
			if k == 'bus2': # is line-like, get value (i.e. the 'to' bus. Note there could be a 'bus3', but these types of object are not eligible for reduction anyway)
				bid = top['bus2']
			if k == 'buses': # is line-like, get 2nd member of tuple (i.e. the 'to' bus)  #(remove?)
				bid = top['buses'][1] #(remove?)
			else:
				continue
		if bid == '': # not a line (or line-like?)
			continue 
		# Strip phase info and apply lookup table to get corresponding bus object (will NOT be of form <object>.<name>)
		bid = _stripPhases(bid) # need to look at circuit to figure out how things are connected. a line is connected to busn.1.2.3 and busn.4.5.6 - is this a switch?
		bus = tree[id2key[bid]] # TODO properly deal with key error when bid=='t_bus3162_l' (HACK: see line 246, 'id2key.update...)
		# Get bottoms' ids, strip off phase info, then apply lookup table to obtain corresponding objects
		bottoms = [] # objects connected to bus
		# loop through tree and grab any objects that have a connection equal to the bus id
		for obj in tree:
			#Loop through dictionary items and get all the connections
			if obj.get('object', None) == top.get('object', None): # The 'top' object is already accounted for
				continue
			#(Could also check for bid equivalency here..?)
			allbottoms = [] # list of ids for connected objects
			for k, v in obj.items():
				if 'bus' in k: # it's a connection attribute (are there any other keys that need to be checked for?)
					if k == 'buses': # it's a tuple, so serialize it for easier processing
						allbottoms.append(obj[k][0])
						allbottoms.append(obj[k][1])
					else: # we'll take it just the way it is
						allbottoms.append(obj[k])
			#if any connection ids equal the node id, then obj is connected to our node of interest
			allbottoms = [_stripPhases(x) for x in allbottoms]
			if ( len([x for x in allbottoms if x == bid]) > 0 ):
				bottoms.append(obj) # and since we already have the object right here, we will just append it instead of using id2key
		# 'bottoms' successfully constructed. now what?
		#Check for a one-line-in, one-line-out scenario
		if len(bottoms) != 1:
			continue
		bottom = bottoms[0]
		# ['r1','r0','x1','x0',c1','c0']
		#if (top.get('geometry','NTC') == bottom.get('geometry','NBC')) and ('length' in top) and ('length' in bottom): # (could configs be defined under any other attribute names?)
		if ('length' in top) and ('length' in bottom): # (could configs be defined under any other attribute names?)
			# delete node and bottom line. Make top line length = sum of both lines. Connect the new bottom.
			newLen = float(top['length']) + float(bottom['length']) # get the new length
			removedids.append(bottom['object'])
			toptree = tree[id2key[top['object']]]
			toptree['length'] = str(newLen)
			toptree['to'] = bottom['to']
			del tree[id2key[bus['name']]]
			del tree[id2key[bottom['name']]]
	#for x in removedids: # DEBUG
	#	print(x)  # DEBUG


def mergeContigLines(tree):
	''' merge all lines that are across nodes and have the same config
	topline --to-> node <-from-- bottomline'''
	removedKeys = 1
	while removedKeys != 0:
		treeKeys = len(tree)
		_mergeContigLinesOnce(tree)
		removedKeys = treeKeys - len(tree)


def _tests():
	# compareVoltsFiles test
	fpath1 = 'ieee240_ours_EXP_VOLTAGES.csv'
	fpath2 = 'ieee240_ours_EXP_VOLTAGES.csv'
	errlim = 0.0
	assert compareVoltsFiles(fpath1, fpath2) <= errlim, 'The error between the compared files exceeds the allowable limit of %s%%.'%(errlim*100)

	# compareVoltsTrees test
	fpath1 = 'ieee240.clean.dss'
	fpath2 = 'ieee240.clean.dss'
	errlim = 0.0
	assert compareVoltsTrees(fpath1, fpath2) <= errlim, 'The error between the compared trees exceeds the allowable limit of %s%%.'%(errlim*100)

	# Contig line merging test
	#FPATH = 'ieee240.clean.dss'
	#import dssConvert
	#tree = dssConvert.dssToTree(FPATH)
	#networkPlot(FPATH) # DEBUG (not working. Line 114 of this file complains about 'BUS2' not having coords)
	#gldtree = dssConvert.evilDssTreeToGldTree(tree) # DEBUG
	#dssConvert.distNetViz.viz_mem(gldtree, open_file=True, forceLayout=True) # DEBUG
	#oldsz = len(tree)
	#mergeContigLines(tree)
	#newsz = len(tree)
	##dssConvert.treeToDss(tree, FPATH[:-4] + '-reduced.dss')
	##networkPlot(FPATH[:-4] +'-reduced.dss') # DEBUG (not working. Line 114 of this file complains about 'BUS2' not having coords)
	##gldtree = dssConvert.evilDssTreeToGldTree(tree) # DEBUG
	##dssConvert.distNetViz.viz_mem(gldtree, open_file=True, forceLayout=True) # DEBUG
	#print('Objects removed: %s (of %s). Percent reduction: %s%%.'%(oldsz, oldsz-newsz, (oldsz-newsz)*100/oldsz))


if __name__ == "__main__":
	_tests()

	# Make core output
	#FPATH = 'ieee240.clean.dss'
	#FPATH = 'ieeeLVTestCaseNorthAmerican.dss'
	#FPATH = 'ieee37.clean.reduced.dss'
	#dssConvert.evilGldTreeToDssTree(tree)
	#dssConvert.treeToDss(tree, 'ieeeLVTestCaseNorthAmerican_reduced.dss')
	

	# Just run DSS
	#runDSS(FPATH)
	# Generate plots, note output is in FPATH dir.
	#voltagePlot(FPATH) # 
	#currentPlot(FPATH)
	#networkPlot(FPATH)
	#THD(FPATH)
	#dynamicPlot(FPATH, 1, 10)
	#faultPlot(FPATH)
	#capacityPlot(FPATH)