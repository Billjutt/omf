''' Calculate the costs and benefits of energy storage from a distribution utility perspective. '''

import os, sys, shutil, csv
from datetime import datetime as dt, timedelta
from os.path import isdir, join as pJoin
from numpy import npv
from omf.models import __neoMetaModel__
from __neoMetaModel__ import *
# from itertools import groupby

# Model metadata:
modelName, template = metadata(__file__)
tooltip = ("The storagePeakShave model calculates the value of a distribution utility " 
	"deploying energy storage based on three possible battery dispatch strategies.")

def work(modelDir, inputDict):
	''' Model processing done here. '''
	out = {}  # See bottom of file for out's structure
	(cellCapacity, dischargeRate, chargeRate, cellQuantity, demandCharge, cellCost) = \
		[float(inputDict[x]) for x in ('cellCapacity', 'dischargeRate', 'chargeRate',
			'cellQuantity', 'demandCharge', 'cellCost')]
	dispatchStrategy = str(inputDict.get('dispatchStrategy'))
	retailCost = float(inputDict.get('retailCost', 0.07))
	projYears = int(inputDict.get('projYears', 10))
	batteryCycleLife = int(inputDict.get('batteryCycleLife', 5000))
	discountRate = float(inputDict.get('discountRate', 2.5)) / 100.0
	dodFactor = float(inputDict.get('dodFactor', 85)) / 100.0

	# Temporarily removed from equations.
	# inverterEfficiency = float(inputDict.get('inverterEfficiency', 92)) / 100.0
	# Note: inverterEfficiency is squared to get round trip efficiency.
	# battEff = float(inputDict.get('batteryEfficiency', 92)) / 100.0 * (inverterEfficiency ** 2)

	with open(pJoin(modelDir, 'demand.csv'), 'w') as f:
		f.write(inputDict['demandCurve'])
	if dispatchStrategy == 'customDispatch':
		with open(pJoin(modelDir, 'dispatchStrategy.csv'), 'w') as f:
			f.write(inputDict['customDispatchStrategy'])

	dc = [] # main data table
	try:
		dates = [(dt(2011,1,1) + timedelta(hours=1)*x) for x in range(8760)]
		with open(pJoin(modelDir, 'demand.csv')) as f:
			reader = csv.reader(f)
			for row, date in zip(reader, dates):
				dc.append({	'datetime': date, 
							'power': float(row[0]), # row is a list of length 1
							'month': date.month - 1,
							'hour': date.hour })
		assert len(dc) == 8760
	except:
		if str(sys.exc_info()[0]) != "<type 'exceptions.SystemExit'>":
			raise Exception("CSV file is incorrect format. Please see valid "
				"format definition at <a target='_blank' href = 'https://github.com/"
				"dpinney/omf/wiki/Models-~-storagePeakShave#demand-file-csv-format'>"
				"\nOMF Wiki storagePeakShave - Demand File CSV Format</a>")

	# list of 12 lists of monthly demands
	demandByMonth = [[t['power'] for t in dc if t['month']==x] for x in range(12)]
	monthlyPeakDemand = [max(lDemands) for lDemands in demandByMonth]
	battCapacity = cellQuantity * cellCapacity * dodFactor
	battDischarge = cellQuantity * dischargeRate
	battCharge = cellQuantity * chargeRate

	# calculate battery's effect and input netpower and battSoC into dc
	SoC = battCapacity  # Battery state of charge; begins full.
	if dispatchStrategy == 'optimal':
		for r in dc:
			powerUnderPeak = monthlyPeakDemand[r['month']] - r['power'] - battDischarge
			charge = (min(powerUnderPeak, battCharge, battCapacity-SoC) if powerUnderPeak > 0 
				else -1 * min(abs(powerUnderPeak), battDischarge, SoC))
			SoC += charge
			r['netpower'] = r['power'] + charge
			r['battSoC'] = SoC
	elif dispatchStrategy == 'daily':
		start = int(inputDict.get('startPeakHour', 18))
		end = int(inputDict.get('endPeakHour', 24))
		for r in dc:
			# Discharge if hour is within peak hours otherwise charge
			charge = (-1*min(battDischarge, SoC) if start <= r['hour'] <= end 
				else min(battCharge, battCapacity - SoC))
			r['netpower'] = r['power'] + charge
			SoC += charge
			r['battSoC'] = SoC
	elif dispatchStrategy == 'customDispatch':
		try:
			with open(pJoin(modelDir,'dispatchStrategy.csv')) as strategyFile:
				reader = csv.DictReader(strategyFile)
				for d, r in zip(dc, reader):
					d['dispatch'] = int(r['dispatch'])
				assert all(['dispatch' in r for r in dc])  # ensure each row is filled
		except:
			if str(sys.exc_info()[0]) != "<type 'exceptions.SystemExit'>":
				raise Exception("Dispatch Strategy file is in an incorrect " 
					"format. Please see valid format definition at <a target "
					"= '_blank' href = 'https://github.com/dpinney/omf/wiki/"
					"Models-~-storagePeakShave#custom-dispatch-strategy-file-"
					"csv-format'>\nOMF Wiki storagePeakShave - Custom "
					"Dispatch Strategy File Format</a>")
		for r in dc:
			# Discharge f there is a 1 in the dispatch strategy csv, otherwise charge the battery.
			charge = (-1*min(battDischarge, SoC) if r['dispatch'] == 1 
				else min(battCharge, battCapacity-SoC))
			r['netpower'] = r['power'] + charge
			SoC += charge
			r['battSoC'] = SoC
	else:
		raise Exception("Invalid dispatch input.")

	# ------------------------- CALCULATIONS ------------------------- #
	netByMonth = [[t['netpower'] for t in dc if t['month']==x] for x in range(12)]
	monthlyPeakNet = [max(net) for net in netByMonth]
	ps = [h-s for h, s in zip(monthlyPeakDemand, monthlyPeakNet)]
	dischargeByMonth = [[i-j for i, j in zip(k, l) if i-j > 0] for k, l in zip(netByMonth, demandByMonth)]

	# Monthly Cost Comparison Table
	out['monthlyDemand'] = [sum(lDemand)/1000 for lDemand in demandByMonth]
	out['monthlyDemandRed'] = [t-p for t, p in zip(out['monthlyDemand'], ps)]
	out['ps'] = ps
	out['kWhtoRecharge'] = [sum(d) for d in dischargeByMonth]
	out['benefitMonthly'] = [x*demandCharge for x in ps]
	out['costtoRecharge'] = [x*retailCost for x in out['kWhtoRecharge']]
	out['benefitNet'] = [b-c for b, c in zip(out['benefitMonthly'], out['costtoRecharge'])]

	# Demand Before and After Storage Graph
	out['demand'] = [t['power']*1000.0 for t in dc]
	out['demandAfterBattery'] = [t['netpower']*1000.0 for t in dc]
	out['batteryDischargekW'] = [d-b for d, b in zip(out['demand'], out['demandAfterBattery'])]
	out['batteryDischargekWMax'] = max(out['batteryDischargekW'])

	# Battery State of Charge Graph
	# Turn dc's SoC into a percentage, with dodFactor considered.
	out['batterySoc'] = SoC = [t['battSoC']/battCapacity*100*dodFactor + (100-100*dodFactor) for t in dc]
	# Estimate number of cyles the battery went through.
	cycleEquivalents = len([c for i, c in enumerate(SoC[:-1]) if SoC[i] < 100 and SoC[i+1] == 100])
	out['cycleEquivalents'] = cycleEquivalents
	out['batteryLife'] = batteryCycleLife / cycleEquivalents

	# Cash Flow Graph
	# cashFlowCurve is $ in from peak shaving minus the cost to recharge the battery every day of the year
	totalYearlyCharge = sum(out['kWhtoRecharge'])
	cashFlowCurve = [(sum(ps) * demandCharge)-(totalYearlyCharge*retailCost) for year in range(projYears)]
	cashFlowCurve.insert(0, -1 * cellCost * cellQuantity)  # insert initial investment
	# simplePayback is also affected by the cost to recharge the battery every day of the year
	out['SPP'] = (cellCost*cellQuantity)/((sum(ps)*demandCharge)-(totalYearlyCharge*retailCost))
	out['netCashflow'] = cashFlowCurve
	out['cumulativeCashflow'] = [sum(cashFlowCurve[:i+1]) for i, d in enumerate(cashFlowCurve)]
	out['NPV'] = npv(discountRate, cashFlowCurve)

	battCostPerCycle = cellQuantity * cellCost / batteryCycleLife
	lcoeTotCost = cycleEquivalents*retailCost + battCostPerCycle*cycleEquivalents
	out['LCOE'] = lcoeTotCost / (cycleEquivalents*battCapacity)

	# Other
	out['startDate'] = '2011-01-01'  # dc[0]['datetime'].isoformat()
	out['stderr'] = ''
	# Seemingly unimportant. Ask permission to delete.
	out['stdout'] = 'Success' 
	out['months'] = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

	return out

def new(modelDir):
	''' Create a new instance of this model. Returns true on success, false on failure. '''
	defaultInputs = {
		# used by __neoMetaModel__.py
		'modelType': modelName,
		'created': '2015-06-12 17:20:39.308239',
		'runTime': '0:00:03',
		'fileName': 'FrankScadaValidCSV_Copy.csv',
		# used for this program
		'batteryEfficiency': '92',
		'inverterEfficiency': '97.5',
		'cellCapacity': '7',
		'discountRate': '2.5',
		'dischargeRate': '5',
		'chargeRate': '5',
		'demandCurve': open(pJoin(__neoMetaModel__._omfDir,'static','testFiles','FrankScadaValidCSV_Copy.csv')).read(),
		'dispatchStrategy': 'daily',
		'cellCost': '7140',
		'cellQuantity': '10',
		'projYears': '15',
		'demandCharge': '20',
		'dodFactor': '97',
		'retailCost': '0.06',
		'startPeakHour': '18',
		'endPeakHour': '22',
		'batteryCycleLife': '5000',
		# required if dispatch strategy is custom
		'customDispatchStrategy': open(pJoin(__neoMetaModel__._omfDir,'static','testFiles','dispatchStrategy.csv')).read(),
	}
	return __neoMetaModel__.new(modelDir, defaultInputs)

def _tests():
	modelLoc = pJoin(__neoMetaModel__._omfDir,'data','Model','admin','Automated Testing of ' + modelName)
	# Blow away old test results if necessary.
	if isdir(modelLoc):
		shutil.rmtree(modelLoc)	
	new(modelLoc)  # Create New.
	renderAndShow(modelLoc)  # Pre-run.
	runForeground(modelLoc)  # Run the model.
	renderAndShow(modelLoc)  # Show the output.

if __name__ == '__main__':
	_tests()

'''
outDic {
	startdate: str
	stdout: "Success"
	batteryDischargekWMax: float
	batteryDischargekw: [8760] float
	monthlyDemandRed: [12] float
	ps: [12] float
	demandAfterBattery: [8760] float
	SPP: float
	kwhtoRecharge [12] float
	LCOE: float
	batteryLife: float
	cumulativeCashflow: [12] float
	batterySoc: [8760] float
	demand: [8760] float
	benefitMonthly: [12] float
	netCashflow: [12] float
	costtoRecharge: [12] float
	months: [12] (strings)
	monthlyDemand: [12] float
	cycleEquivalents: float
	stderr: ""
	NPV: float
	benefitNet: 12
}

# insert into work()
	# ------------------------ DEBUGGING TOOLS ----------------------- #
	# import matplotlib.pyplot as plt 
	# dcThroughTheMonth = [[t for t in iter(dc) if t['month']<=x] for x in range(12)]
	# hoursThroughTheMonth = [len(dcThroughTheMonth[month]) for month in range(12)]
	# # Output some matplotlib results as well.
	# plt.plot([t['power'] for t in dc])
	# plt.plot([t['netpower'] for t in dc])
	# plt.plot([t['battSoC'] for t in dc])
	# for month in range(12):
	#   plt.axvline(hoursThroughTheMonth[month])
	# plt.savefig(pJoin(modelDir,"plot.png"))

'''
