ifcbAdmin.controller('InstrumentCtrl', ['$scope', 'InstrumentService', 'TimeSeriesService', 'Restangular', function ($scope, InstrumentService, TimeSeriesService, Restangular) {


    // initialize local scope
    $scope.alert = null;
    $scope.restore = {};

    // load iniital data from api
    TimeSeriesService.list.then(function(serverResponse) {
        $scope.time_series = serverResponse;
    }, function(errorResponse) {
        console.log(errorResponse);
        $scope.alert = 'Unexpected ' + errorResponse.status.toString()
            + ' error while loading data from server.'
    });

    // load iniital data from api
    InstrumentService.list.then(function(serverResponse) {
        $scope.instruments = serverResponse;
    }, function(errorResponse) {
        console.log(errorResponse);
        $scope.alert = 'Unexpected ' + errorResponse.status.toString()
            + ' error while loading data from server.'
    });

    // create new timeseries
    $scope.addNewInstrument = function() {
        $scope.instruments.push(InstrumentService.new());
        return true;
    }


    // mark timeseries group for editing
    $scope.editInstrument = function(instr) {
        $scope.restore[instr.id] = {};
        angular.copy(instr, $scope.restore[instr.id]);
        instr.edit = true;
    }

    // mark timeseries group for editing
    $scope.cancelInstrument = function(instr) {
        if (instr.id) {
            // cancel edit on saved timeseries
            // restore unedited copy
            angular.copy($scope.restore[instr.id], instr);
            delete $scope.restore[instr.id];
        } else {
            // cancel creation of new timeseries
            $scope.instruments  = _.without($scope.instruments, instr);
        }
    }

    // save timeseries group to server
    $scope.saveInstrument = function(instr) {
        if(instr.id) {
            // timeseries group already exists on server. update.
	    instr.patch().then(function(serverResponse) {
                delete instr.edit;
                delete $scope.restore[instr.id];
                $scope.alert = null;
            }, function(serverResponse) {
                console.log(serverResponse);
                $scope.alert = serverResponse.data.validation_errors;
            });
	    return true;
        } else {
            // new instrument. post to server.
            InstrumentService.post(instr).then(function(serverResponse) {
                // copy server response to scope object
                angular.copy(serverResponse, instr);
                $scope.alert = null;
            }, function(serverResponse) {
                console.log(serverResponse);
                $scope.alert = serverResponse.data.validation_errors;
            });
        }
    }

    // remove timeseries group
    $scope.removeInstrument = function(instr) {
        instr.remove().then(function() {
            $scope.instruments = _.without($scope.instruments, instr);
        });
    }
    
$scope.$on('$locationChangeStart', function( event ) {
	if($.isEmptyObject($scope.restore)) {
		return;
	}
	$.each($scope.instruments, function(ix, ts) {
		if(ts.edit) {
			$scope.cancelInstrument(ts);
			ts.edit = false;
		}
	});
});

}]);
