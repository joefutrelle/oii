

var ifcbAdmin = angular.module('ifcbAdmin', []);



ifcbAdmin.controller('TimeSeriesController', function($scope) {

    $scope.timeseries = [
        {
            "enabled": false,
            "name": "testseries1",
            "systempaths": [
                "/Users/marknye"
            ],
            "uri": "http://localhost:8080/admin/api/v1.0/timeseries/1"
        }
    ];

});
