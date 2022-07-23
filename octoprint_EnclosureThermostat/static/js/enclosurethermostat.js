$(function() {
    function EnclosureThermostatViewModel(parameters) {
        var self = this;
		self.pluginName = "EnclosureThermostat";
		self.global_settings = parameters[0];
		self.EnclTemp = ko.observable("");
		self.CurMode = ko.observable("");
		self.EnclStatus = ko.observable("");
		self.TargetTempVal = ko.observable("");
		self.TargetTempVis = ko.observable(false);
		self.GlobalTargTemp = ""
		self.newArrayY = ko.observableArray();
		self.newArrayX = ko.observableArray();
		self.ChartData = ko.observableArray();
		
		self.onBeforeBinding = function () {
            self.settings = self.global_settings.settings.plugins.EnclosureThermostat;
        };
				
		self.thermostatoff = function() {
			$.ajax({
				type: "GET",
				dataType: "json",
				url: self.buildPluginUrl("/thermostatoff"),
				success: function(data) {
					new PNotify({
							title: "Thermostat Off",
							text: "",
							type: "success",
							hide: true
						});
					}
			});
		};
		self.thermostatfilmode = function() {

			mode = $("#FilamentType").val();
			var request = {"mode": mode};
			$.ajax({
				type: "GET",
				dataType: "json",
				data: request,
				url: self.buildPluginUrl("/thermostatfilament"),
				success: function(data) {
					new PNotify({
							title: "Thermostat Update",
							text: "Filament Mode",
							type: "success",
							hide: true
						});
					}
			});
		};

		self.thermostatmantemp = function() {
			tempval = $("#mantempval").val();
			try {
				tempval = parseInt(tempval);
				let comparenumber = Number.isFinite(tempval);
				if (comparenumber){
					if (tempval >60 && tempval < 121){					
						var request = {"tempval": tempval};
						$.ajax({
							type: "GET",
							dataType: "json",
							data: request,
							url: self.buildPluginUrl("/thermostatmantemp"),
							success: function(data) {
								new PNotify({
										title: "Thermostat Update",
										text: "Manual Temp Mode",
										type: "success",
										hide: true
									});
								}
						});
				}
			}
			} catch (error) {

			}				
		};
		
		self.thermostatmanpwm = function() {
			pwmtempval = $("#manpwmval").val();
			try {
				pwmtempval = parseInt(pwmtempval);
				let comparenumber = Number.isFinite(pwmtempval);
				if (comparenumber){
					if (pwmtempval >= 0 && pwmtempval <= 100){					
						var request = {"tempval": pwmtempval};
						$.ajax({
							type: "GET",
							dataType: "json",
							data: request,
							url: self.buildPluginUrl("/thermostatmanpwm"),
							success: function(data) {
								new PNotify({
										title: "Thermostat Update",
										text: "PWM Mode",
										type: "success",
										hide: true
									});
								}
						});
				}
			}
			} catch (error) {

			}				
		};		
	
		self.onDataUpdaterPluginMessage = function(plugin, data) {
			if (plugin != "EnclosureThermostat") {
				return;
			}
			if(data.type == "popup") {
				new PNotify({
					title: data.title,
					text: data.msg,
					type: data.alertype,
					hide: true
					});
			}
			if (data.enclosureTemp){
				self.EnclTemp(data.enclosureTemp)
			}
			if (data.enclosuretargettemp){
				if (self.GlobalTargTemp == "FILA" || self.GlobalTargTemp == "TEMP"){
					self.TargetTempVis(true);
					self.TargetTempVal(String(data.enclosuretargettemp));
				} else {
					self.TargetTempVis(false);
				}	
			}
			if (data.enclosureMode){
				self.GlobalTargTemp = String(data.enclosureMode);
				self.CurMode(data.enclosureMode)
			}
			if (data.enclosureStatus){
				self.EnclStatus(data.enclosureStatus)
				self.EnclosureStatus = String(data.enclosureStatus)
				if (self.EnclosureStatus == "Cooling") {
					$("#EnclosureStatusValue").attr('class', 'cooling');
				} else if (self.EnclosureStatus == "Heating") {
					$("#EnclosureStatusValue").attr('class', 'heating');
				} else  {
					$("#EnclosureStatusValue").attr('class', 'regular');
				}
			}
        }
		self.buildPluginUrl = function (path) {
		  return window.PLUGIN_BASEURL + self.pluginName + path;
		};
	//Graph
    var arrayLength = 120
	//var newArrayY = []
	//var newArrayX = []
	
	
	for(var i = 0; i < arrayLength; i++) {
		var x = new Date();
		self.newArrayX().push(x);
		var y = self.EnclTemp(); //Math.round(parseInt(self.EnclTemp()));
		self.newArrayY().push(y);
	}

	Plotly.newPlot('graph', [{
	  x: [self.newArrayX()], 
	  y: [self.newArrayY()],
	  mode: 'lines',
	  line: {color: '#80CAF6'}
	}]);  

	var cnt = 0;

	var interval = setInterval(function() {
	  var tempint = parseInt(self.EnclTemp());
	  let comparetemp = Number.isFinite(tempint);
		if (comparetemp){
		  var x = new Date();
		  self.newArrayX().push(x)
		  self.newArrayX().splice(0, 1)	  
		  var y = self.EnclTemp();
		  self.newArrayY().push(y)
		  self.newArrayY().splice(0, 1)
		  
		  var data_update = {
		  x: [self.newArrayX()],
		  y: [self.newArrayY()]
		  };
		  
		  Plotly.update('graph', data_update)
		} 
	  if(cnt === 500) clearInterval(interval);
	}, 5000);
	
	
	
    }


    OCTOPRINT_VIEWMODELS.push({
        construct: EnclosureThermostatViewModel,
		dependencies: ["settingsViewModel"],
        elements: ["#navbar_plugin_EnclosureThermostat", "#settings_plugin_EnclosureThermostat", "#tab_plugin_EnclosureThermostat"]
    });
});