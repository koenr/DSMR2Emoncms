#!/bin/bash
#
# Watchdog file for checking correct behaviour of main process
#
# Auteur : Edwin Bontenbal
# Email  : Edwin.Bontenbal@Gmail.COM
FILE="/tmp/DSMR2Emoncms_Watchdog"
LOGFILE="/var/log/DSMR2Emoncms_Watchdog.log"
PROCESS="/usr/bin/python3 /usr/local/bin/DSMR2Emoncms.py"
TimeNow=$(date +%s)
ProcessID=$(pgrep -f DSMR2Emoncms.py)

WriteLog() {
    echo "$(date) $1" >> $LOGFILE
}

if [ -f "$FILE" ];
then
    # File exists
    TimeInWatchdogFile=$(cat "$FILE")
    TimeDifference=$((TimeNow - TimeInWatchdogFile))

    # Check leegte eerst, daarna pas het tijdsverschil berekenen (fix: volgorde omgedraaid)
    if [ "$TimeInWatchdogFile" != "" ] && [ "$TimeDifference" -gt "60" ];
    then
        # Time difference is too big
        WriteLog "Watchdog file found."
        WriteLog "Time difference is too big ($TimeDifference), now it is $TimeNow and the file contains ($TimeInWatchdogFile)."
        if [ -z "$ProcessID" ];
        then
            # No process found, start it
            WriteLog "No ProcessID ($ProcessID) belonging to Process ($PROCESS) found, start it!"
            $PROCESS >/dev/null 2>&1 &
        else
            # Process seems to be running but something is wrong, kill it and restart
            WriteLog "ProcessID ($ProcessID) belonging to Process ($PROCESS) found, but something is wrong, kill it hard and start it!"
            kill -9 "$ProcessID"
            rm -f "$FILE"
            $PROCESS >/dev/null 2>&1 &
        fi
    fi
else
    # File does not exist
    WriteLog "Watchdog file does not exist."
    if [ -z "$ProcessID" ];
    then
        # No process found, start it
        WriteLog "No ProcessID ($ProcessID) belonging to Process ($PROCESS) found, start it!"
        $PROCESS >/dev/null 2>&1 &
    else
        # Process seems to be running but something is wrong, kill it and restart
        WriteLog "ProcessID ($ProcessID) belonging to Process ($PROCESS) found, but something is wrong, kill it hard and start it!"
        kill -9 "$ProcessID"
        rm -f "$FILE"
        $PROCESS >/dev/null 2>&1 &
    fi
fi
