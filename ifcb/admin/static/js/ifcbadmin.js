

// create AngularJS application
var ifcbAdmin = angular.module('ifcbAdmin', ['ngRoute']);

// application controllers container
var controllers = {};

// time series controller
controllers.TimeSeriesController = function($scope) {

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

};

// users controller
controllers.UsersController = function($scope) {

    $scope.users = [];
}

// my account controller
controllers.MyAccountController = function($scope) {

    $scope.myaccount = [];
}

// bind controllers to application
ifcbAdmin.controller(controllers);

// define application routes
ifcbAdmin.config(['$routeProvider', function($routeProvider) {
    $routeProvider.
        when('/timeseries', {
            controller: 'TimeSeriesController',
            templateUrl: 'views/TimeSeries.html'
            }).
        when('/users', {
            controller: 'UsersController',
            templateUrl: 'views/Users.html'
            }).
        when('/myaccount', {
            controller: 'MyAccountController',
            templateUrl: 'views/MyAccount.html'
            }).
        otherwise({
            redirectTo: '/timeseries'
        });
}]);



