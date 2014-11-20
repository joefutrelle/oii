ifcbAdmin.controller('InstrumentCtrl', ['$scope', 'Restangular', function ($scope, Restangular) {


    // initialize local scope
    var baseInstruments = Restangular.all('instruments');
    $scope.alert = null;

    // initialize local scope
    var baseTimeSeries = Restangular.all('time_series');
    $scope.alert = null;
    var restore = {};

    // load iniital data from api
    baseTimeSeries.getList().then(function(serverResponse) {
        $scope.time_series = serverResponse;
    }, function(errorResponse) {
        console.log(errorResponse);
        $scope.alert = 'Unexpected ' + errorResponse.status.toString()
            + ' error while loading data from server.'
    });

    // load iniital data from api
    baseInstruments.getList().then(function(serverResponse) {
        $scope.instruments = serverResponse;
    }, function(errorResponse) {
        console.log(errorResponse);
        $scope.alert = 'Unexpected ' + errorResponse.status.toString()
            + ' error while loading data from server.'
    });

    // create new timeseries
    $scope.addNewInstrument = function() {
        $scope.instruments.push({name:'',data_path:'',edit:true});
        return true;
    }


    // mark timeseries group for editing
    $scope.editInstrument = function(instr) {
        restore[instr.id] = {};
        angular.copy(instr, restore[instr.id]);
        instr.edit = true;
    }

    // mark timeseries group for editing
    $scope.cancelInstrument = function(instr) {
        if (instr.id) {
            // cancel edit on saved timeseries
            // restore unedited copy
            angular.copy(restore[instr.id], instr);
            delete restore[instr.id];
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
                delete restore[instr.id];
                $scope.alert = null;
        }, function(serverResponse) {
                console.log(serverResponse);
                $scope.alert = serverResponse.data.validation_errors;
        });
        } else {
        // new timeseries group. post to server.
        baseInstruments.post(instr).then(function(serverResponse) {
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

}]);
