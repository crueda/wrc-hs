#!/usr/bin/env python
#-*- coding: UTF-8 -*-

# autor: Ignacio Gilbaja
# date: 2015-07-01
# version: 1.1

##################################################################################
# version 1.0 release notes: extract data from MySQL and generate json
# Initial version
# Requisites: library python-mysqldb. To install: "apt-get install python-mysqldb"
##################################################################################


import MySQLdb
import logging, logging.handlers
import os
import time
import json
import sys

#### VARIABLES #########################################################
from configobj import ConfigObj
config = ConfigObj('/opt/gen-json/visor_wrc.properties')
#config = ConfigObj('./visor_wrc.properties')

INTERNAL_LOG_FILE = config['directory_logs'] + "/visor_wrc.log"
LOG_FOR_ROTATE = 10

MYSQL_IP = config['mysql_host']
MYSQL_PORT = config['mysql_port']
MYSQL_USER = config['mysql_user']
MYSQL_NAME = config['mysql_db_name']
MYSQL_PASSWORD = config['mysql_passwd']

INTERNAL_LOG = "/tmp/kyros-json.log"

PID = "/var/run/json-generator"

from json import encoder
encoder.FLOAT_REPR = lambda o: format(o, '.4f')


########################################################################
# definimos los logs internos que usaremos para comprobar errores
log_folder = os.path.dirname(INTERNAL_LOG)

if not os.path.exists(log_folder):
	os.makedirs(log_folder)

try:
	logger = logging.getLogger('wrc-json')
	loggerHandler = logging.handlers.TimedRotatingFileHandler(INTERNAL_LOG , 'midnight', 1, backupCount=10)
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	loggerHandler.setFormatter(formatter)
	logger.addHandler(loggerHandler)
	logger.setLevel(logging.DEBUG)
except:
	print '------------------------------------------------------------------'
	print '[ERROR] Error writing log at %s' % INTERNAL_LOG
	print '[ERROR] Please verify path folder exits and write permissions'
	print '------------------------------------------------------------------'
	exit()
########################################################################

########################################################################
if os.access(os.path.expanduser(PID), os.F_OK):
        print "Checking if json generator is already running..."
        pidfile = open(os.path.expanduser(PID), "r")
        pidfile.seek(0)
        old_pd = pidfile.readline()
        # process PID
        if os.path.exists("/proc/%s" % old_pd) and old_pd!="":
			print "You already have an instance of the json generator running"
			print "It is running as process %s," % old_pd
			sys.exit(1)
        else:
			print "Trying to start json generator..."
			os.remove(os.path.expanduser(PID))

pidfile = open(os.path.expanduser(PID), 'a')
print "json generator started with PID: %s" % os.getpid()
pidfile.write(str(os.getpid()))
pidfile.close()
#########################################################################


def getTracking():
	dbKyros4 = MySQLdb.connect(MYSQL_IP, MYSQL_USER, MYSQL_PASSWORD, MYSQL_NAME)
	try:
		dbKyros4 = MySQLdb.connect(MYSQL_IP, MYSQL_USER, MYSQL_PASSWORD, MYSQL_NAME)
	except:
		logger.error('Error connecting to database: IP:%s, USER:%s, PASSWORD:%s, DB:%s', MYSQL_IP, MYSQL_USER, MYSQL_PASSWORD, MYSQL_NAME)

	cursor = dbKyros4.cursor()
#	cursor.execute("""SELECT TRACKING_1.VEHICLE_LICENSE as DEV, POS_LATITUDE_DEGREE + POS_LATITUDE_MIN/60 as LAT, POS_LONGITUDE_DEGREE + POS_LONGITUDE_MIN/60 as LON, VEHICLE.START_STATE as STATUS from TRACKING_1 join (VEHICLE, HAS, FLEET) where TRACKING_1.VEHICLE_LICENSE = HAS.VEHICLE_LICENSE and TRACKING_1.VEHICLE_LICENSE = VEHICLE.VEHICLE_LICENSE and HAS.FLEET_ID=FLEET.FLEET_ID and (FLEET.FLEET_ID=489 || FLEET.FLEET_ID=498)""" )
	cursor.execute("""SELECT VEHICLE.ALIAS as DRIVER, round(POS_LATITUDE_DEGREE,4) + round(POS_LATITUDE_MIN/60,4) as LAT, round(POS_LONGITUDE_DEGREE,4) + round(POS_LONGITUDE_MIN/60,4) as LON, VEHICLE.START_STATE as TRACKING_STATE, VEHICLE_EVENT_1.TYPE_EVENT as VEHICLE_STATE, TRACKING_1.VEHICLE_LICENSE as DEV from TRACKING_1 join (VEHICLE, HAS, FLEET, VEHICLE_EVENT_1) where TRACKING_1.VEHICLE_LICENSE = HAS.VEHICLE_LICENSE and TRACKING_1.VEHICLE_LICENSE = VEHICLE.VEHICLE_LICENSE and VEHICLE_EVENT_1.VEHICLE_LICENSE = VEHICLE.VEHICLE_LICENSE and HAS.FLEET_ID=FLEET.FLEET_ID and (FLEET.FLEET_ID=489 || FLEET.FLEET_ID=498) """)
	result = cursor.fetchall()
	
	try:
		return result
	except Exception, error:
		logger.error('Error getting data from database: %s.', error )
		
	cursor.close
	dbFrontend.close

while True:
	array_list = []
	trackingInfo = getTracking()

	for tracking in trackingInfo:
	#	lonRound = float("{0:.4f}".format(tracking[2]))
	#	print lonRound
	#	latRound = float("{0:.4f}".format(tracking[1]))
	#	print latRound
		position = {"geometry": {"type": "Point", "coordinates": [ tracking[2] , tracking[1] ]}, "type": "Feature", "properties":{"alias":str(tracking[0]), "tracking_state":str(tracking[3]), "vehicle_state":str(tracking[4]), "license":str(tracking[5])}}
		array_list.append(position)

	with open('/var/www2/tracking_wrc.json', 'w') as outfile:
		json.dump(array_list, outfile)
	
	time.sleep(2)
