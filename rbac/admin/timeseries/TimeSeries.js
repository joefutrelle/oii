

ifcbAdmin.controller('TimeSeriesCtrl', ['$scope', 'TimeSeriesService', function ($scope, TimeSeriesService) {

    // initialize local scope
    $scope.alert = null;
    var restore = {};

    // load iniital data from api
    TimeSeriesService.list.then(function(serverResponse) {
        $scope.time_series = serverResponse;
    }, function(errorResponse) {
        console.log(errorResponse);
        $scope.alert = 'Unexpected ' + errorResponse.status.toString()
            + ' error while loading data from server.'
    });

    // create new timeseries
    $scope.addNewTimeSeries = function() {
        $scope.time_series.push(TimeSeriesService.new());
        return true;
    }

    // create new
    $scope.addNewPath = function(ts) {
        ts.data_dirs.push({path:'',product_type:'raw'});
    }

    // mark timeseries group for editing
    $scope.editTimeSeries = function(ts) {
        restore[ts.id] = {};
        angular.copy(ts, restore[ts.id]);
        ts.edit = true;
    }

    // mark timeseries group for editing
    $scope.cancelTimeSeries = function(ts) {
        if (ts.id) {
            // cancel edit on saved timeseries
            // restore unedited copy
            angular.copy(restore[ts.id], ts);
            delete restore[ts.id];
        } else {
            // cancel creation of new timeseries
            $scope.time_series  = _.without($scope.time_series, ts);
        }
    }

    // save timeseries group to server
    $scope.saveTimeSeries = function(ts) {
	console.log("saving time series "+ts.label);
        // remove blank paths before save
        for (var i = 0; i < ts.data_dirs.length; i++) {
            if (ts.data_dirs[i].path.trim() == "") {
                $scope.removePath(ts, ts.data_dirs[i]);
            }
        }
        if(ts.id) {
        // timeseries group already exists on server. update.
        ts.patch().then(function(serverResponse) {
                delete ts.edit;
                delete restore[ts.id];
                $scope.alert = null;
        }, function(serverResponse) {
                console.log(serverResponse);
                $scope.alert = serverResponse.data.validation_errors;
        });
        } else {
        // new timeseries group. post to server.
        TimeSeriesService.post(ts).then(function(serverResponse) {
                // copy server response to scope object
                angular.copy(serverResponse, ts);
                $scope.alert = null;
        }, function(serverResponse) {
                console.log(serverResponse);
                $scope.alert = serverResponse.data.validation_errors;
        });
        }
    }

    $scope.checkPathsTimeSeries = function(ts) {
	var check_url = '/' + ts.label + '/api/check_roots';
 	var message = "No data found for "+ts.label;
	$.getJSON(check_url, function(r) {
	    message = "";
	    $.each(r, function(root, found) {
		if(found) {
		    message = message + "Data found in "+root+". ";
		} else {
		    message = message + "NO DATA FOUND in "+root+"! ";
		}
	    });
	    $scope.alert = message;
	    $scope.$apply();
	});
    }

    $scope.accedeTimeSeries = function(ts) {
	var check_url = '/' + ts.label + '/api/check_roots';
  	var accession_url = "/" + ts.label + "/api/accede";
	$.getJSON(check_url, function(r) {
            var someNotFound = false;
	    $.each(r, function(root, found) {
		if(!found) {
                    $scope.alert = "ERROR: no data found in " + root + ".";
		    $scope.$apply();
		    someNotFound = true;
                }
            });
	    if(!someNotFound) {
		$scope.alert = "Data found, attempting to initiate accession for " + ts.label;
		$scope.$apply();
		$.getJSON(accession_url, function(r) {
		    $scope.alert = "Data found, accession initiated for "+ts.label;
		    $scope.$apply();
		});
            }
        });
    };

    // remove timeseries group
    $scope.removeTimeSeries = function(ts) {
        ts.remove().then(function() {
            $scope.time_series = _.without($scope.time_series, ts);
        });
    }

    // remove path
    $scope.removePath = function(ts,p) {
        // remove only from local scrope
        // server is updated with saveTimeSeries()
        ts.data_dirs = _.without(ts.data_dirs, p);
    }

}]);
