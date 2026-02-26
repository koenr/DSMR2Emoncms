#This utility sends a P1 (smartmeter) telegram to emoncms
#  
# coded by:
# Auteur : Edwin Bontenbal
# Email  : Edwin.Bontenbal@Gmail.COM 
version = "v1.07"
# VERSION    DATE        ADDED FUNCTIONALITY
# 1.05       03-05-2017  Config file added
# 1.06       04-05-2017  3 fase metering added
# 1.07       26-02-2025  Koen Roggemans - koen@roggemans.net - Converting python2 to python3; Meter type selection via config; minor bugfixes;
#                        unified  regex (\d+\w*) for both meter types

# if errors during executing this script make sure you installed python and the required modules/libraries
import configparser
import serial
import datetime
import time
import logging
import re
import json
import crcmod
import urllib.request
import sys

# Set variables for logging
LogFile              = "/var/log/DSMR2Emoncms.log"
LogFileLastTelegram  = "/tmp/DSMR2Emoncms_p1Telegram.log"
WatchdogFile         = "/tmp/DSMR2Emoncms_Watchdog"

# Set logging params
logging.basicConfig(filename=LogFile, format='%(asctime)s %(message)s', level=logging.DEBUG)

# Open and read config file
Config = configparser.ConfigParser()
Config.read("/etc/DSMR2Emoncms/DSMR2Emoncms.cfg")

def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            logging.debug("Reading config file : " + section + "," + option + " = " + dict1[option])
        except:
            dict1[option] = None
    return dict1

# Set emoncms variables
emon_privateKey = ConfigSectionMap("emoncms")['privatekey']
emon_node       = ConfigSectionMap("emoncms")['node']
emon_host       = ConfigSectionMap("emoncms")['host']
emon_protocol   = ConfigSectionMap("emoncms")['protocol']
emon_url        = ConfigSectionMap("emoncms")['url']

# Set COM port config
ser          = serial.Serial()
ser.baudrate = 115200
ser.bytesize = serial.EIGHTBITS
ser.parity   = serial.PARITY_NONE
ser.stopbits = serial.STOPBITS_ONE
ser.xonxoff  = 1
ser.rtscts   = 0
ser.timeout  = 20
ser.port     = ConfigSectionMap("serial")['port']

###############################################################################################################
# DSMR field definitions per meter type
# Format: [label, OBIS_regex, value_regex, emoncms_key]
#
# Config file [meter] section:
#   type = sagemcom_xt211   (default)
#   type = kaifa_ma105
###############################################################################################################

DSMR_LISTS = {
    "sagemcom_xt211": [
        ["DayConsumption",       "1-0:1\.8\.2",            "\d{6}\.\d{3}", "DagGebruik"],
        ["NightConsumption",     "1-0:1\.8\.1",            "\d{6}\.\d{3}", "NachtGebruik"],
        ["DayGenerated",         "1-0:2\.8\.2",            "\d{6}\.\d{3}", "DagLevering"],
        ["NightGenerated",       "1-0:2\.8\.1",            "\d{6}\.\d{3}", "NachtLevering"],
        ["WaterConsumption",     "0-1:24\.2\.1\(\d+\w*\)", "\d{5}\.\d{3}", "Waterverbruik"],
        ["ActualConsumption",    "1-0:1\.7\.0",            "\d{2}\.\d{3}", "ActueelVerbruik"],
        ["ActualGenerated",      "1-0:2\.7\.0",            "\d{2}\.\d{3}", "ActueelLevering"],
        ["ActualConsumption_L1", "1-0:21\.7\.0",           "\d{2}\.\d{3}", "ActueelVerbruik_L1"],
        ["ActualConsumption_L2", "1-0:41\.7\.0",           "\d{2}\.\d{3}", "ActueelVerbruik_L2"],
        ["ActualConsumption_L3", "1-0:61\.7\.0",           "\d{2}\.\d{3}", "ActueelVerbruik_L3"],
        ["ActualGenerated_L1",   "1-0:22\.7\.0",           "\d{2}\.\d{3}", "ActueelLevering_L1"],
        ["ActualGenerated_L2",   "1-0:42\.7\.0",           "\d{2}\.\d{3}", "ActueelLevering_L2"],
        ["ActualGenerated_L3",   "1-0:62\.7\.0",           "\d{2}\.\d{3}", "ActueelLevering_L3"],
        ["Voltage_L1",           "1-0:32\.7\.0",           "\d{3}\.\d",    "Spanning_L1"],
        ["Voltage_L2",           "1-0:52\.7\.0",           "\d{3}\.\d",    "Spanning_L2"],
        ["Voltage_L3",           "1-0:72\.7\.0",           "\d{3}\.\d",    "Spanning_L3"],
        ["Current_L1",           "1-0:31\.7\.0",           "\d{3}\.\d",    "Stroom_L1"],
        ["Current_L2",           "1-0:51\.7\.0",           "\d{3}\.\d",    "Stroom_L2"],
        ["Current_L3",           "1-0:71\.7\.0",           "\d{3}\.\d",    "Stroom_L3"],
    ],
    "kaifa_ma105": [
        ["NightConsumption",     "1-0:1\.8\.1",            "\d{6}\.\d{3}", "NachtGebruik"],
        ["DayConsumption",       "1-0:1\.8\.2",            "\d{6}\.\d{3}", "DagGebruik"],
        ["NightGenerated",       "1-0:2\.8\.1",            "\d{6}\.\d{3}", "NachtLevering"],
        ["DayGenerated",         "1-0:2\.8\.2",            "\d{6}\.\d{3}", "DagLevering"],
        # \d+\w* (zero or more non-digit chars) is used consistently for the timestamp suffix
        ["GasConsumption",       "0-1:24\.2\.1\(\d+\w*\)", "\d{5}\.\d{3}", "GasGebruik"],
        ["ActualTarif",          "0-0:96\.14\.0",          "\d{4}",        "ActueleTarief"],
        ["ActualConsumption",    "1-0:1\.7\.0",            "\d{2}\.\d{3}", "ActueleGebruik"],
        ["ActualConsumption_L1", "1-0:21\.7\.0",           "\d{2}\.\d{3}", "ActueleGebruik_L1"],
        ["ActualConsumption_L2", "1-0:41\.7\.0",           "\d{2}\.\d{3}", "ActueleGebruik_L2"],
        ["ActualConsumption_L3", "1-0:61\.7\.0",           "\d{2}\.\d{3}", "ActueleGebruik_L3"],
        ["ActualGenerated",      "1-0:2\.7\.0",            "\d{2}\.\d{3}", "ActueleLevering"],
        ["ActualGenerated_L1",   "1-0:22\.7\.0",           "\d{2}\.\d{3}", "ActueleLevering_L1"],
        ["ActualGenerated_L2",   "1-0:42\.7\.0",           "\d{2}\.\d{3}", "ActueleLevering_L2"],
        ["ActualGenerated_L3",   "1-0:62\.7\.0",           "\d{2}\.\d{3}", "ActueleLevering_L3"],
    ],
}

# Load meter type from config; fall back to sagemcom_xt211 if not set
meter_type = ConfigSectionMap("meter").get("type", "sagemcom_xt211").strip().lower()

if meter_type not in DSMR_LISTS:
    sys.exit("Onbekend metertype '%s' in config. Kies uit: %s" % (meter_type, ", ".join(DSMR_LISTS.keys())))

DSMR_List = DSMR_LISTS[meter_type]
logging.warning("Metertype geladen: %s (%d velden)" % (meter_type, len(DSMR_List)))

###############################################################################################################
# Main program
###############################################################################################################

# Initialize
p1_telegram  = False
p1_timestamp = ""
p1_log       = True

p1_complete_telegram_raw = ""
p1_complete_telegram     = ""

# Show startup arguments
logging.warning("Port: (%s)" % (ser.name))

# Open COM port
try:
    ser.open()
    ser.rts = True   # P1 poort vereist RTS hoog om data te sturen (Data Request pin)
    ser.dtr = True
except:
    logging.warning("Error opening port %s." % ser.name)
    sys.exit("Error opening port %s." % ser.name)

while p1_log:
    try:
        p1_raw = ser.readline().decode('utf8', errors='ignore')
    except:
        logging.warning("Error reading port %s." % ser.name)
        ser.close()
        sys.exit("Error reading port %s." % ser.name)

    p1_complete_telegram_raw += p1_raw

    # Check if the buffer contains a complete telegram
    if re.search('/.*!\w{4}', p1_complete_telegram_raw, re.DOTALL) is not None:
        logging.warning("Telegram found")

        # Extract complete telegram
        found_telegram = re.search('.*(?P<Y>/.*!\w{4})', p1_complete_telegram_raw, re.DOTALL).group(1)

        # Write timestamp to watchdog file
        with open(WatchdogFile, "w") as f3:
            f3.write(str(int(time.time())))

        # Write telegram to log file  (bug fix: was f1.close without parentheses)
        with open(LogFileLastTelegram, "w") as f1:
            f1.write(found_telegram)

        logging.debug(p1_complete_telegram_raw)

        # Extract CRC from telegram
        crc_in_telegram = re.search(r".*!(?P<Y>.{4})", found_telegram, re.DOTALL).group(1)

        # Calculate CRC of received telegram
        crcstring = re.search(r'(?P<Y>\/.*!)', found_telegram, re.DOTALL)
        crc16     = crcmod.predefined.mkPredefinedCrcFun('crc16')
        crc_data  = crcstring.group(1).encode('utf-8')
        crc_value = crc16(crc_data)
        crc_calculated = re.search(r'0X(?P<Y>\w{0,4})', hex(crc_value).upper()).group(1)

        if crc_calculated.lstrip("0") == crc_in_telegram.lstrip("0"):
            logging.debug("ok    checksum. Calculated: " + crc_calculated + " telegram: " + crc_in_telegram)
            DataJson = {}
            for x in range(len(DSMR_List)):
                matchObj = re.search(r"" + DSMR_List[x][1] + "\((?P<Y>" + DSMR_List[x][2] + ")",
                                     p1_complete_telegram_raw, re.DOTALL)
                if matchObj is not None:
                    logging.debug("Item found     : " + DSMR_List[x][1])
                    DataJson[DSMR_List[x][3]] = float(matchObj.group(1))
                else:
                    logging.debug("Item NOT found : " + DSMR_List[x][1])

            url = (emon_protocol + emon_host + emon_url +
                   "node=" + emon_node +
                   "&apikey=" + emon_privateKey +
                   "&json=" + str(json.dumps(DataJson, separators=(',', ':'))))
            logging.debug(url)
            HTTPresult = urllib.request.urlopen(url)
            logging.debug("Response code : " + str(HTTPresult.getcode()))

            p1_complete_telegram_raw = ""
        else:
            logging.debug("wrong checksum. Calculated: " + crc_calculated + " telegram: " + crc_in_telegram)
            p1_complete_telegram_raw = ""

# Clean shutdown
logging.warning("Main loop exited, closing port %s." % ser.name)
ser.close()
