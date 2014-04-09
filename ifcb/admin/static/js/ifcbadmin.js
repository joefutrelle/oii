

// create AngularJS application
var ifcbAdmin = angular.module('ifcbAdmin', ['ngRoute','restangular']);

// configure Restangular for flask restless endpoints
ifcbAdmin.config(function(RestangularProvider) {

    RestangularProvider.setBaseUrl('/admin/api/v1');

    RestangularProvider.setResponseExtractor(function(response, operation) {
        // This is a get for a list
        var newResponse;
        if (operation === 'getList') {
            // Return the result objects as an array and attach the metadata
            newResponse = response.objects;
            newResponse.metadata = {
                numResults: response.num_results,
                page: response.page,
                totalPages: response.total_pages
            };
        } else {
            // This is an element
            newResponse = response;
        }
      return newResponse;
    });
});

// nav controller
ifcbAdmin.controller('NavigationCtrl', ['$scope', '$location', function ($scope, $location) {
    $scope.isCurrentPath = function (path) {
      return $location.path() == path;
    };
}]);

ifcbAdmin.controller('TimeSeriesCtrl', ['$scope', 'Restangular', function ($scope, Restangular) {

    var baseTimeSeries = Restangular.all('timeseries');
    $scope.timeseries = baseTimeSeries.getList().$object;

    $scope.editTimeSeries = function(ts) {
        ts.edit = true;
    }

    $scope.saveTimeSeries = function(ts) {
        delete ts.edit;
    }

}]);

// users controller
ifcbAdmin.controller('UsersCtrl', ['$scope', function ($scope) {

    $scope.users = [];
}]);

// my account controller
ifcbAdmin.controller('AccountCtrl', ['$scope', function ($scope) {

    $scope.myaccount = [];
}]);


// define application routes
ifcbAdmin.config(['$routeProvider', function($routeProvider) {
    $routeProvider.
        when('/timeseries', {
            controller: 'TimeSeriesCtrl',
            templateUrl: 'views/TimeSeries.html'
            }).
        when('/users', {
            controller: 'UsersCtrl',
            templateUrl: 'views/Users.html'
            }).
        when('/myaccount', {
            controller: 'AccountCtrl',
            templateUrl: 'views/MyAccount.html'
            }).
        otherwise({
            redirectTo: '/timeseries'
        });
}]);



