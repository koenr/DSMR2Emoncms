# DSMR2Emoncms

install emoncms on a sever for example a raspberry pi

run the following commands on a raspberry py

# Prerequisites
```sh
# Install python
sudo apt-get install python3 python3-pip -y

# Install python libraries
sudo pip3 install pyserial crcmod requests --break-system-packages
```

# Install on rasberian
```sh 
cd /var/tmp
git clone -b master https://github.com/koenr/DSMR2Emoncms.git
cd DSMR2Emoncms/
cp DSMR2Emoncms.py /usr/local/bin/DSMR2Emoncms.py
cp DSMR2EmoncmsWatchdog.sh /usr/local/bin/DSMR2EmoncmsWatchdog.sh
mkdir /etc/DSMR2Emoncms
cp DSMR2Emoncms_default.cfg  /etc/DSMR2Emoncms/DSMR2Emoncms.cfg

```` 

add to crontab
```sh 
sudo crontab -e
```
add
```sh 
* * * * * /usr/local/bin/DSMR2EmoncmsWatchdog.sh >> /var/log/DSMR2EmoncmsWatchdog.cron.log 2>&1
@reboot sleep 30 && /usr/local/bin/DSMR2EmoncmsWatchdog.sh >> /var/log/DSMR2EmoncmsWatchdog.cron.log 2>&1


```

set logrotate
``` sh
cd /etc/logrotate.d
vi DSMR2Emoncms
```
add
``` sh
/var/log/DSMR2Emoncms_Watchdog.log /var/log/DSMR2EmoncmsWatchdog.cron.log  {
    daily
    rotate 7
    compress
    missingok
    notifempty
    size 10M
}
```
and
``` sh
/var/log/DSMR2Emoncms*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    size 10M
    olddir /var/log.old/DSMR2Emoncms
    createolddir 755 root root
    renamecopy
    postrotate
        kill -HUP $(pgrep -f DSMR2Emoncms.py) 2>/dev/null || true
    endscript
}
```

Now change the settings in the file DSMR2Emoncms.py
```
vi /etc/DSMR2Emoncms/DSMR2Emoncms.cfg
privateKey = <YOUR APIKEY OF EMONCMS INSTANCE> 
emon_host  = <YOUR IP OF EMONCMS INSTANCE>

If needed change the serial port "ser.port" preffered method is by-id. 
ls -l /dev/serial/by-id/
# results in "usb-FTDI_USB__-__Serial-if00-port0"
ser.port     = "/dev/serial/by-id/usb-FTDI_USB__-__Serial-if00-port0"

Choose the correct meter by uncommenting the correct line.
```

 
