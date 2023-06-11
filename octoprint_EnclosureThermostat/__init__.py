import octoprint.plugin
from octoprint.util import RepeatedTimer
import sys
import os
import serial as s
import time
from flask import jsonify, request, make_response, Response
from octoprint.events import Events


#Call all Plugins
class EnclosurethermostatPlugin(octoprint.plugin.StartupPlugin,
                                octoprint.plugin.TemplatePlugin,
                                octoprint.plugin.AssetPlugin,
                                octoprint.plugin.SettingsPlugin,
                                octoprint.plugin.BlueprintPlugin,
                                octoprint.plugin.EventHandlerPlugin):
                                
    def __init__(self):
        self.printing = False
        self._checkTempTimer = None
        self._ThermostatTimeoutTimer = None
        self.ThermostatTimeoutBool = False
        self.temp = 0
        self.mode = ""
        self.status = ""
        self.TargetTemp = ""
        self.FanSpeed = ""
        self.serialconnected = False
        self.arduino = s.Serial()  #Define Serial
        self.RequestCommandProcess = False
    def checkthermobool(self):
        if self.ThermostatTimeoutBool:
            return True
        else:
            return False
        
    def sendcommand(self, command):
        if (self.RequestCommandProcess == False):
            self.RequestCommandProcess = True
            try:
                if self.serialconnected:
                    self._logger.info(f"Sending Command {command}")
                    self.arduino.write(command.encode('utf-8'))
                    time.sleep(0.1)
                    response = self.arduino.readline().decode().strip()
                    self.arduino.flush()
                    self._logger.info(self.temp)
                    if response != "500" or response != "" or response is not None:
                        self._logger.info(f"Command Successfull: {command}")
                        self.RequestCommandProcess = False
                        return response
                    else: 
                        self._logger.info(f"Command Failed: {command}")
                        self.RequestCommandProcess = False
                        return "error"
                return "error"
            except Exception as e:
                self._logger.error(f"Enclosure Thermostat Encountered an Issue Sending Command {command}: {e}")
                self.RequestCommandProcess = False
                return "error"

    def start_Thermostat_Timeout_Timer(self, interval):
        self._ThermostatTimeoutTimer = RepeatedTimer(interval, self.mythermostatofftimer, condition=self.checkthermobool, run_first=False)
        self._ThermostatTimeoutTimer.start() 

    def stop_Thermostat_Timeout_Timer(self):
        self._ThermostatTimeoutTimer.cancel()

    def start_tempcheck_timer(self, interval):
        self._checkTempTimer = RepeatedTimer(interval, self.get_enclosure_temp, run_first=True)
        self._checkTempTimer.start() 

    def connect_serial_thermo(self):
        #Serial Connection
        try:
            self.arduino.port=self.comport
            self.arduino.baudrate=self.baudrate
            self.arduino.timeout=0
            #arduino.setDTR(False)
            #arduino.rtscts = True
            self.arduino.open()
            self._logger.info("Enclosure Thermostat Serial Connected.")
            os.system('stty -F /dev/Temp_Controller -hupcl')
            time.sleep(1)
            self.start_tempcheck_timer(5)
            self.serialconnected = True
            self._plugin_manager.send_plugin_message(self._identifier, dict(type="popup", title="Thermostat Connected", msg="", alertype="success"))
        except Exception as e:
            self.serialconnected = False
            self._plugin_manager.send_plugin_message(self._identifier, dict(type="popup", title="Thermostat Error", msg="Could not Connect to Thermostat", alertype="error"))
            self._logger.error("Enclosure Thermostat Connection Failed: %s" % (e))
            self.stop_tempcheck_timer()
    
    def mythermostatofftimer(self):
            try:
                if self.ThermostatTimeoutBool:
                    self.ThermostatTimeoutBool = False
                    self.stop_Thermostat_Timeout_Timer()
                    response = self.sendcommand("<M0>")
                    if (response == "200"):
                        self._logger.info("Enclosure Thermostat Turned Off due to Timeout.")
                    else: 
                        self._logger.error("Enclosure Thermostat Could not be turned off.")
            except Exception as e:
                self._logger.error("Enclosure Thermostat Encountered an Issue: ")
   
    ##~~ Blueprint Reader

    @octoprint.plugin.BlueprintPlugin.route("/thermostatdelayed", methods=["GET"])
    def thermostattimeout(self):
        try:
            if self.ThermostatTimeoutBool:
                self.ThermostatTimeoutBool = False
                self.stop_Thermostat_Timeout_Timer()
            return jsonify(success=True)
        except:
            self._logger.error("Enclosure Thermostat Encountered an Issue: 1")
            return jsonify(success=False)

    @octoprint.plugin.BlueprintPlugin.route("/thermostatoff", methods=["GET"])
    def mythermostatoff(self):
        try:
            response = self.sendcommand("<M0>")
            if response == "200":
                if self.ThermostatTimeoutBool:
                    self.ThermostatTimeoutBool = False
                    self.stop_Thermostat_Timeout_Timer()
                return jsonify(success=True)
            else:
                return jsonify(success=False)
        except Exception as e:
            self._logger.error(f"Enclosure Thermostat Encountered an Issue: {e}")
            return jsonify(success=False)

        
    @octoprint.plugin.BlueprintPlugin.route("/thermostatfilament", methods=["GET"])
    def mythermostatfilament(self):
        try:
            data = request.values["mode"]
            response = self.sendcommand("<M1>")
            if response == "200":
                self._logger.info(f"Mode changed: Filament Temp")
                response = self.sendcommand(f"<F{data}>")
                if response == "200":
                    self._logger.info(f"Filament changed: {data}")
                    return jsonify(success=True)
            return jsonify(success=False)
        except Exception as e:
            self._logger.error(f"Enclosure Thermostat Encountered an Issue: {e}")
            return jsonify(success=False)
        
    @octoprint.plugin.BlueprintPlugin.route("/thermostatmantemp", methods=["GET"])
    def mythermostatmantemp(self):
        try:
            data = request.values["tempval"]
            response = self.sendcommand("<M2>")
            if response == "200":
                self._logger.info(f"Mode changed: Manual Temp")
                response = self.sendcommand(f"<T{data}>")
                if response == "200":
                    self._logger.info(f"Manual Target Temp changed: {data}")
                    return jsonify(success=True)
            return jsonify(success=False)
        except Exception as e:
            self._logger.error(f"Enclosure Thermostat Encountered an Issue: {e}")
            return jsonify(success=False)  

    @octoprint.plugin.BlueprintPlugin.route("/coolpid", methods=["GET"])
    def mycoolpid(self):
        try:
            data = request.values["tempval"]
            response = self.sendcommand("<M4>")
            if response == "200":
                self._logger.info(f"Mode changed: Target Temp Cool")
                response = self.sendcommand(f"<T{data}>")
                if response == "200":
                    self._logger.info(f"Manual Target Cool Temp changed: {data}")
                    return jsonify(success=True)
            return jsonify(success=False)
        except Exception as e:
            self._logger.error(f"Enclosure Thermostat Encountered an Issue: {e}")
            return jsonify(success=False)      

    @octoprint.plugin.BlueprintPlugin.route("/thermostatmanpwm", methods=["GET"])
    def mythermostatmanpwm(self):
        try:
            data = request.values["tempval"]
            response = self.sendcommand("<M3>")
            if response == "200":
                self._logger.info(f"Mode changed: Manual PWM")
                response = self.sendcommand(f"<P{data}>")
                if response == "200":
                    self._logger.info(f"Manual PWM Fan Speed Changed: {data}")
                    return jsonify(success=True)
            return jsonify(success=False)
        except Exception as e:
            self._logger.error(f"Enclosure Thermostat Encountered an Issue: {e}")
            return jsonify(success=False)    
        
    def turnoff(self):
        try:
            if self.serialconnected:
                self._plugin_manager.send_plugin_message(self._identifier, dict(type="endprint", title="Thermostat Turning Off!", msg="Printing Stopped", alertype="success"))
      
        except:
            self._logger.error("Enclosure Thermostat Encountered an Issue: 1")
            self._plugin_manager.send_plugin_message(self._identifier, dict(type="popup", title="Thermostat Error", msg="Thermostat Could not be turned off", alertype="error"))

    
    def get_serialconnectcheck(self):
        try:
            self.arduino.inWaiting()
        except:
            self._logger.error("Enclosure Thermostat Not Connected.. Retrying Connection")
            self.connect_serial_thermo()
       
    def start_serialconnectioncheck_timer(self, interval):
        self._checkTempTimer = RepeatedTimer(interval, self.get_serialconnectcheck, run_first=True)
        self._checkTempTimer.start() 
 
    def on_after_startup(self):
        self._logger.info("Enclosure Thermostat Started.")
        self.comport = self._settings.get(["comport"])
        self.baudrate = self._settings.get(["baudrate"])
        self.showenclosuretemp = self._settings.get(["showenclosuretemp"])
        self.showmode = self._settings.get(["showmode"])
        self.showstatus = self._settings.get(["showstatus"])
        self.showtargettemp = self._settings.get(["showtargettemp"])
        self.stopprintaftercancel = self._settings.get(["stopprintaftercancel"])
        self.stopprintafterfinish = self._settings.get(["stopprintafterfinish"])
        self.stopprintaftererror = self._settings.get(["stopprintaftererror"])
        self.start_serialconnectioncheck_timer(30)
        
    def stop_tempcheck_timer(self):
        self._checkTempTimer.cancel()
        
    def on_event(self, event, payload):
        if event == octoprint.events.Events.PRINT_FAILED:
            self.printing = False
            if self._settings.get(["stopprintaftererror"]):
                self.start_Thermostat_Timeout_Timer(20)
                self.ThermostatTimeoutBool = True
                self.turnoff()
        if event == octoprint.events.Events.PRINT_DONE:
            self.printing = False
            if self._settings.get(["stopprintaftererror"]):
                self.start_Thermostat_Timeout_Timer(20)
                self.ThermostatTimeoutBool = True
                self.turnoff()
        if event == octoprint.events.Events.PRINT_CANCELLED:
            self.printing = False
            if self._settings.get(["stopprintaftercancel"]):
                self.start_Thermostat_Timeout_Timer(20)
                self.ThermostatTimeoutBool = True
                self.turnoff()
        if event == octoprint.events.Events.PRINT_STARTED:
            self.printing = True
    
    def custom_atcommand_handler(self, comm, phase, command, parameters, tags=None, *args, **kwargs):
        if self.printing and command == "THERMOSTAT_COOL":
            if parameters:
                self._logger.info(f"THERMOSTAT_COOL: {parameters}")  
                valuesetting = parameters.strip()
                if valuesetting.isdigit():
                    valuesetting = valuesetting
                    try:
                        response = self.sendcommand("<M4>")
                        if response == "200":
                            self._logger.info(f"Mode changed: Target Temp Cool")
                            response = self.sendcommand(f"<T{valuesetting}>")
                            if response == "200":
                                self._logger.info(f"Manual Target Cool Temp changed: {valuesetting}")
                                self._plugin_manager.send_plugin_message(self._identifier, dict(type="popup", title="Cooling Mode Enabled!", msg=f"Cooling set to: {valuesetting}F", alertype="success"))   
                    except Exception as e:
                        self._logger.error(f"Enclosure Thermostat Encountered an Issue: {e}")

        if self.printing and command == "THERMOSTAT_MAN":
            if parameters:
                self._logger.info(f"THERMOSTAT_MAN: {parameters}")  
                valuesetting = parameters.strip()
                if valuesetting.isdigit():
                    valuesetting = valuesetting
                    try:
                        response = self.sendcommand("<M2>")
                        if response == "200":
                            self._logger.info(f"Mode changed: Manual Temp")
                            response = self.sendcommand(f"<T{valuesetting}>")
                            if response == "200":
                                self._logger.info(f"Manual Target Temp changed: {valuesetting}")
                                self._plugin_manager.send_plugin_message(self._identifier, dict(type="popup", title="Manual Tempurature Mode Enabled!", msg=f"Temperature set to: {valuesetting}F", alertype="success"))   
                    except Exception as e:
                        self._logger.error(f"Enclosure Thermostat Encountered an Issue: {e}")
            
        if self.printing and command == "THERMOSTAT_PWM":
            if parameters:
                self._logger.info(f"THERMOSTAT_PWM: {parameters}")  
                valuesetting = parameters.strip()
                if valuesetting.isdigit():
                    valuesetting = valuesetting
                    try:
                        response = self.sendcommand("<M3>")
                        if response == "200":
                            self._logger.info(f"Mode changed: Manual PWM")
                            response = self.sendcommand(f"<P{valuesetting}>")
                            if response == "200":
                                self._logger.info(f"Manual PWM Fan Speed Changed: {valuesetting}")
                                self._plugin_manager.send_plugin_message(self._identifier, dict(type="popup", title="PWM Mode Enabled!", msg=f"Fan set to: {valuesetting}%", alertype="success"))
                    except Exception as e:
                        self._logger.error(f"Enclosure Thermostat Encountered an Issue: {e}")

    def get_enclosure_temp(self):
            #Get Temp
            try:

                response = self.sendcommand("<SInternalTemp>")
                if response != "error" or response is not None:
                    self.temp = response
                    self._logger.info("Enclosure Temp: " + self.temp)
                    self._plugin_manager.send_plugin_message(self._identifier,
                                                             dict(enclosureTemp=str(self.temp) + '\u00b0F'))

                response = self.sendcommand("<SMode>")
                if response != "error" or response is not None:
                    self.mode = response
                    self._logger.info("Enclosure Mode: " + self.mode)
                    self._plugin_manager.send_plugin_message(self._identifier,
                                                             dict(enclosureMode=str(self.mode)))
                                   
                response = self.sendcommand("<SStatus>")
                if response != "error" or response is not None:
                    self.status = response
                    self._logger.info("Enclosure Status: " + self.status)
                    self._plugin_manager.send_plugin_message(self._identifier,
                                                             dict(enclosureStatus=str(self.status)))

                if (self.mode == "FILA"):
                    response = self.sendcommand("<SFilamentTemp>")
                    if response != "error" or response is not None:
                        self.TargetTemp = response
                        self._logger.info("Target Temp: " + self.TargetTemp)
                        self._plugin_manager.send_plugin_message(self._identifier,
                                                                    dict(enclosuretargettemp=str(self.TargetTemp)))
                elif (self.mode == "TEMP"):
                    response = self.sendcommand("<SManualTargetTemp>")
                    if response != "error" or response is not None:
                        self.TargetTemp = response
                        self._logger.info("Target Temp: " + self.TargetTemp)
                        self._plugin_manager.send_plugin_message(self._identifier,
                                                                    dict(enclosuretargettemp=str(self.TargetTemp)))
                elif (self.mode == "COOL"):
                    response = self.sendcommand("<SManualTargetTemp>")
                    if response != "error" or response is not None:
                        self.TargetTemp = response
                        self._logger.info("Target Temp: " + self.TargetTemp)
                        self._plugin_manager.send_plugin_message(self._identifier,
                                                                    dict(enclosuretargettemp=str(self.TargetTemp)))
                else:
                    self._logger.info("Target Temp: None")
                    self._plugin_manager.send_plugin_message(self._identifier,
                                                                dict(enclosuretargettemp="None"))                    

            except Exception as e:
                self._logger.error(f"Enclosure Thermostat Not Connected.. Retrying Connection Error: {e}")
                self.connect_serial_thermo()
                                                
    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
        # for details.
        return dict(
            Enclosurethermostat=dict(
                displayName="OctoPrint-Enclosurethermostat",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="myevo8u",
                repo="OctoPrint-Enclosurethermostat",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/myevo8u/OctoPrint-Enclosurethermostat/archive/{target_version}.zip"
            )
        )                                            
 
    def get_template_configs(self):
        try:
            return [
                dict(type="navbar", template="enclosurethermostat_navbar.jinja2"),
                dict(type="settings", template="enclosurethermostat_settings.jinja2"),
                dict(type="tab", template="enclosurethermostat_tab.jinja2")
            ]
        except Exception:
            return []
            
    def get_settings_defaults(self):
        return dict(comport="/dev/Temp_Controller", baudrate="9600", showenclosuretemp=True, showmode=True, showstatus=True, showtargettemp=True, stopprintaftercancel=True, stopprintafterfinish=True, stopprintaftererror=True)
        
 
    def get_assets(self):
        return dict(
            js=["js/enclosurethermostat.js", "js/plotly-2.12.1.min.js"],
            css=["css/enclosurethermostat.css"]
        )

__plugin_name__ = "Enclosurethermostat"
__plugin_pythoncompat__ = ">=3.7,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = EnclosurethermostatPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.atcommand.queuing": __plugin_implementation__.custom_atcommand_handler
    }