

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
        $scope.time_series.push(TimeSeriesService.newTimeSeries());
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
    // perform accession on the time series (FIXME this may be slow!)
    // FIXME this uses jQuery
    accession_url = "/" + ts.label + "/api/accession";
    $scope.alert = "Saving time series...";
    $.getJSON(accession_url, function(r) {
        var total = r.total
        $scope.alert = total + " bin(s) found";
    });
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
