#!/usr/bin/python3

from gi.repository import GLib
import dbus
import time
import signal
import math
from dbus_types import *
import subprocess

import dbus.mainloop.glib
import argparse
import os,sys,logging
import configparser
import contextlib 
"""
#https://stackoverflow.com/questions/865115/how-do-i-correctly-clean-up-a-python-object
# use the gps_locator as:
# with gps_locator() as gps_obj :
#    use the gps_obj
#NEEDED at all??
"""
class Package(object):
    def __new__(cls, *args, **kwargs):
        package = super(Package, cls).__new__(cls)
        package.__init__(*args, **kwargs)
        return contextlib.closing(package)

def list_add(a,b) :
  if len(a) == 0 :
    return b
  if len(a) == len(b) :
    return list(map(sum,zip(a,b)))
  else :
    raise Exception('incompatible arguments')
    
def list_mult_scalar(a,b) :
    return [b * v for v in a]  


class gps_locator(Package):
  hybris_geo = None
  hybris_pos = None
  hybris_velo = None
  hybris_sat = None
 
  connect_geo = None
  connect_pos = None
  connect_sat = None
  sats = [0,0]
  accum_pos = []
  accum_err = 0
  av_pos = []
  track = []
  tracking = False
  timeout = None
  required_accuracy = None
  exit_gps = None
  gpslogger = None

  def close(self):
      pass        

  def __init__(self,exit_function, t_o = 120, a_t = 10,logger = None): #exit_function is a callback function which will receive the gps coordinates (takes a string argument)
    self.required_accuracy = a_t
    self.exit_gps = exit_function
    self.gpslogger = logger
    if self.check_positioning_enabled() :
      dbus_hybris = dbus.SessionBus().get_object('org.freedesktop.Geoclue.Providers.Hybris', '/org/freedesktop/Geoclue/Providers/Hybris')
      
      self.hybris_geo = dbus.Interface(dbus_hybris, 'org.freedesktop.Geoclue')
      self.hybris_pos = dbus.Interface(dbus_hybris, 'org.freedesktop.Geoclue.Position')
      self.hybris_velo = dbus.Interface(dbus_hybris, 'org.freedesktop.Geoclue.Velocity')
      self.hybris_sat = dbus.Interface(dbus_hybris, 'org.freedesktop.Geoclue.Satellite')
     
      self.hybris_geo.AddReference()
      self.status_update (self.hybris_geo.GetStatus())
     
      self.connect_geo = self.hybris_geo.connect_to_signal(signal_name = "StatusChanged", handler_function = self.status_update)
      self.connect_pos = self.hybris_pos.connect_to_signal(signal_name = "PositionChanged", handler_function = self.position_update)
      self.connect_sat = self.hybris_sat.connect_to_signal(signal_name = "SatelliteChanged", handler_function = self.sat_update)
      self.timeout = GLib.timeout_add_seconds(t_o, self.end_gps_location)
    else :
      self.exit_gps("Sorry, error enabling gps")
    
  def check_positioning_enabled(self):
    config = configparser.ConfigParser()
    if not os.path.isfile('/etc/location/location.conf') :
      if self.gpslogger : self.gpslogger.info ("no configuration file... cannot continue")
      return False
    try :
      config.read('/etc/location/location.conf')
      settings = config['location']
      need_enabling= False
      if settings['enabled'] != 'true' :
        if self.gpslogger : self.gpslogger.info ("location disabled altogether... enabling")
        need_enabling= True
      elif self.gpslogger : self.gpslogger.info ("location enabled")
      if settings['gps\\enabled'] != 'true' :
        if self.gpslogger : self.gpslogger.info ("gps disabled... enabling")
        need_enabling= True  
      elif self.gpslogger : self.gpslogger.info ("gps enabled")
      if (settings['mls\\enabled'] == 'true') and (settings['mls\\agreement_accepted'] == 'true') and (settings['mls\\online_enabled'] == 'true'):
        if self.gpslogger : self.gpslogger.info ("Mozilla location service (agps) enabled")
        #if not, we could enable data radio (wifi or cellular) and mls
        # for the moment do nothing 
    except Exception as e:
      if self.gpslogger : self.gpslogger.info ("error reading localisation config file :".format(e))
      return False
    if need_enabling :
      return self.enable_gps()
    else :
      return True
  
  
  def enable_gps(self): #needs sudo and a line in sudoers
    try:
      subprocess.check_call("sudo /bin/sed -i 's|^enabled=false|enabled=true|' /etc/location/location.conf", shell=True)
      subprocess.check_call("sudo /bin/sed -i 's|^gps\\enabled=false|gps\\enabled=true|' /etc/location/location.conf", shell=True)
      #subprocess.check_call(sys.path[0]+"/enable_gps", shell=True)
      if self.gpslogger : self.gpslogger.info ("gps enabled")
      return True
    except subprocess.CalledProcessError as e: 
      if self.gpslogger : self.gpslogger.info ("error enabling gps : {}\nCheck the presence of sudo and content of sudoers file".format(e))
      return False
  
  def status_update (self,arg):
    status_dic={0:"Error", 1:"Unavailable", 2:"Acquiring", 3:"Available"}
    if self.gpslogger : self.gpslogger.info ("gps status: %s"%(status_dic[arg]))
    
  def sat_update (self,timestamp, satellite_used, satellite_visible, used_prn, sat_info) :
    if self.sats != dbus2py([satellite_used,satellite_visible]) :
      self.sats = dbus2py([satellite_used,satellite_visible])
      if self.gpslogger : self.gpslogger.info ("satellites used: %s; visible: %s"%(self.sats[0],self.sats[1]))
    #print(dbus2py(used_prn))
    #print(dbus2py(sat_info))
  
  
  def position_update (self,fields,timestamp,latitude,longitude,altitude,accuracy):
    cur_pos = dbus2py([latitude,longitude,altitude])
    accuracy = dbus2py(accuracy[1])
    if self.gpslogger : self.gpslogger.info ("new position: %s, precision %s"%(cur_pos, accuracy))
    self.speed,self.direction = [dbus2py(v) for v in self.hybris_velo.GetVelocity()[2:4]]
    self.speed *= 1.852
    #print (self.speed, " ", self.direction)
    av_err = 1000
    if (self.speed < 2.5) or ((not math.isnan(self.speed)) and math.isnan(self.direction)) : #not moving, we can average sucessive position readings to increase accuracy
      acc2 = pow(accuracy,-2)
      self.accum_pos = list_add(self.accum_pos, list_mult_scalar(cur_pos , acc2))
      self.accum_err += acc2
      av_err = math.sqrt(1/self.accum_err)
      self.av_pos = list_mult_scalar(self.accum_pos , 1/self.accum_err)+[av_err]
      if self.gpslogger : self.gpslogger.info ("average position: %s, precision %s"%(self.av_pos, av_err))
    else :
      if self.gpslogger : self.gpslogger.info ("moving: %s km/h, direction : %s"%(self.speed, self.direction))
      self.tracking = True
      self.track.append(cur_pos[:2])     
    if (not self.tracking) and (min(av_err, accuracy) < self.required_accuracy) : #else wait timeout
      if self.gpslogger : self.gpslogger.info ("\nAccuracy reached!\n")
      self.end_gps_location()
  
  def end_gps_location(self):
      GLib.source_remove(self.timeout)
      self.connect_pos.remove()
      self.connect_geo.remove()
      self.connect_sat.remove()
      self.hybris_geo.RemoveReference()
      msg = ""
      if self.tracking :
        msg = "The phone is moving!\nLast speed : %s km/h ; direction : %s\n"%(self.speed,self.direction)
        msg = msg + """The last position was
https://www.openstreetmap.org/?mlat=%s&mlon=%s&zoom=15
"""%(self.track[-1][0],self.track[-1][1])
        msg = msg + "The recorded track is \n%s\n"%(self.track)
      if self.av_pos != [] :
        #if self.gpslogger : self.gpslogger.info("averaged coordinate : %s"%(self.av_pos))
        msg = msg+"""With a precision of %sm the phone is at
geo:%s,%s
https://www.openstreetmap.org/?mlat=%s&mlon=%s&zoom=15
"""%(int(self.av_pos[3]),self.av_pos[0],self.av_pos[1],self.av_pos[0],self.av_pos[1])
      if msg == "" :
        msg = "\nGPS timed out... \nSatellites used : %s ; visible %s"%(self.sats[0],self.sats[1])
      if self.gpslogger : self.gpslogger.info(msg)
      self.exit_gps(msg)
    
def exit_local (dummy) :
    #print("exit_local")
    mainloop.quit() 
    


if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument("-t", "--timeout", type=int,  default=120,
                      help="Maximum time (in seconds) the program will run, trying to get a fix, to reach the requested accuracy or collecting a track")
                      
  parser.add_argument("-a", "--accuracy", type=int,  default=10,
                      help="requested accuracy, in meters")
  args = parser.parse_args()
  time_out = args.timeout
  accuracy_target = args.accuracy
  
  mainloop = GLib.MainLoop()
  dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
  
  logfile="{0}/{1}".format(sys.path[0], "gps.log")
  try:
    os.remove(logfile)
  except OSError as e:  ## if failed, report it back to the user ##
    print ("Error: %s - %s." % (e.filename, e.strerror))
      
  logging.basicConfig(
    level=logging.INFO,
    #format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
    format="%(message)s",
    handlers=[
      logging.FileHandler(logfile),
      logging.StreamHandler(sys.stdout)
    ])
  logger = logging.getLogger()
  
  try:
    with gps_locator(exit_local,time_out,accuracy_target,logger)  as gps :
      mainloop.run()
  except KeyboardInterrupt:
    if logger : logger.info('Ctrl+C hit, quitting')
    gps.end_gps_location()

