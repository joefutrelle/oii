

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

ifcbAdmin.controller('TimeSeriesCtrl', ['$scope', 'Restangular', function ($scope, Restangular) {

    // initialize local scope
    var baseTimeSeries = Restangular.all('timeseries');
    $scope.alert = null;

    // load iniital data from api
    baseTimeSeries.getList().then(function(serverResponse) {
        $scope.timeseries = serverResponse;
    }, function(errorResponse) {
        console.log(errorResponse);
        $scope.alert = 'Unexpected ' + errorResponse.status.toString()
            + ' error while loading data from server.'
    });

    // create new timeseries
    $scope.addNewTimeSeries = function() {
        $scope.timeseries.push({name:'',systempaths:[{path:''}],edit:'true'});
        return true;
    }

    // create new path
    $scope.addNewPath = function(ts) {
        ts.systempaths.push({path:''});
    }

    // mark timeseries group for editing
    $scope.editTimeSeries = function(ts) {
        ts.edit = true;
    }

    // save timeseries group to server
    $scope.saveTimeSeries = function(ts) {
        // remove blank paths before save
        for (var i = 0; i < ts.systempaths.length; i++) {
            if (ts.systempaths[i].path.trim() == "") {
                $scope.removePath(ts, ts.systempaths[i]);
            }
        }
        if(ts.id) {
            // timeseries group already exists on server. update.
            ts.patch().then(function(serverResponse) {
                delete ts.edit;
                $scope.alert = null;
            }, function(serverResponse) {
                console.log(serverResponse);
                $scope.alert = serverResponse.data.validation_errors;
            });
        } else {
            // new timeseries group. post to server.
            baseTimeSeries.post(ts).then(function(serverResponse) {
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
            $scope.timeseries = _.without($scope.timeseries, ts);
        });
    }

    // remove path
    $scope.removePath = function(ts,p) {
        // remove only from local scrope
        // server is updated with saveTimeSeries()
        ts.systempaths = _.without(ts.systempaths, p);
    }

}]);

// users controller
ifcbAdmin.controller('UserCtrl', ['$scope', 'Restangular', function ($scope, Restangular) {

    // initialize local scope
    var baseUsers = Restangular.all('users');
    $scope.alert = null;

    // load iniital data from api
    baseUsers.getList().then(function(serverResponse) {
        $scope.users = serverResponse;
    }, function(errorResponse) {
        console.log(errorResponse);
        $scope.alert = 'Unexpected ' + errorResponse.status.toString()
            + ' error while loading data from server.'
    });

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
            controller: 'UserCtrl',
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



