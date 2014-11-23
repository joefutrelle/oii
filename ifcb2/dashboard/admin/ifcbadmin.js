
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

// confirmation popup
ifcbAdmin.directive('ngConfirmClick', [function() {
    return {
        restrict: 'A',
        link: function(scope, element, attrs) {
            element.bind('click', function() {
                var condition = scope.$eval(attrs.ngConfirmCondition);
                if(condition) {
                    var message = attrs.ngConfirmMessage;
                    if (message && confirm(message)) {
                        scope.$apply(attrs.ngConfirmClick);
                    }
                } else {
                    scope.$apply(attrs.ngConfirmClick);
                }
            });
        }
    }
}]);

// nav controller
ifcbAdmin.controller('NavigationCtrl', ['$scope', '$location', function ($scope, $location) {
    $scope.isCurrentPath = function (path) {
      return $location.path() == path;
    };
}]);

// define application routes
ifcbAdmin.config(['$routeProvider', function($routeProvider) {
    $routeProvider.
        when('/time_series', {
            controller: 'TimeSeriesCtrl',
            templateUrl: '/admin/timeseries/TimeSeries.html'
            }).
        when('/users', {
            controller: 'UserCtrl',
            templateUrl: '/admin/users/Users.html'
            }).
        when('/myaccount', {
            controller: 'AccountCtrl',
            templateUrl: '/admin/myaccount/MyAccount.html'
            }).
        when('/instruments', {
            controller: 'InstrumentCtrl',
            templateUrl: '/admin/instruments/Instruments.html'
	    }).
        when('/keychain', {
            controller: 'KeyChainCtrl',
            templateUrl: '/admin/keychain/Keychain.html'
        }).
        otherwise({
            redirectTo: '/time_series'
        });
}]);
