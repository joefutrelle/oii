

// users controller
ifcbAdmin.controller('UserCtrl', ['$scope', 'UserService', 'RoleService', 'Restangular', function ($scope, UserService, RoleService, Restangular) {

    // initialize local scope
    $scope.alert = null;
    $scope.newuser = false;
    var restore = {};

    // load iniital data from api
    RoleService.list.then(function(serverResponse) {
        $scope.roles = serverResponse;
    }, function(errorResponse) {
        console.log(errorResponse);
        $scope.alert = 'Unexpected ' + errorResponse.status.toString()
            + ' error while loading data from server.'
    });

    UserService.list.then(function(serverResponse) {
        $scope.users = serverResponse;
    }, function(errorResponse) {
        console.log(errorResponse);
        $scope.alert = 'Unexpected ' + errorResponse.status.toString()
            + ' error while loading data from server.'
    });

    // save user to server
    $scope.saveUser = function(user) {
        // user will log in with email + password
        // so here username will always be set to email address
        user.username = user.email;
        if(user.id) {
            // user already exists on server. update.
            user.patch().then(function(serverResponse) {
                delete user.edit;
                delete restore[user.id];
                $scope.alert = null;
            }, function(serverResponse) {
                console.log(serverResponse);
                $scope.alert = serverResponse.data.validation_errors;
            });
        } else {
            // new user. post to server.
            UserService.post(user).then(function(serverResponse) {
                // copy server response to scope object
                $scope.users.push(serverResponse);
                $scope.newuser = false;
                $scope.alert = null;
            }, function(serverResponse) {
        console.log("OK, that didn't work"); // FIXME debug
                console.log(serverResponse);
                $scope.alert = serverResponse.data.validation_errors;
            });
        }
    }

    // create new user
    $scope.addNewUser = function() {
        $scope.newuser = UserService.new();
    }

    // cancel new user creation
    $scope.cancelUser = function(user) {
        if (user.id) {
            // cancel edit on saved timeseries
            // restore unedited copy
            angular.copy(restore[user.id], user);
            delete restore[user.id];
        } else {
            $scope.newuser = false;
        }
    }

    $scope.editUser = function(user) {
        restore[user.id] = {}
        angular.copy(user, restore[user.id]);
        user.edit = true;
    }

    // disable user toggle
    $scope.toggleUser = function(user) {
        tmpuser = user.clone();
        tmpuser.is_enabled = !tmpuser.is_enabled;
        tmpuser.patch().then(function(serverResponse) {
            user.is_enabled = !user.is_enabled;
        });
    }

    $scope.setPassword = function(user) {
        $scope.userpw = user;
    }

    $scope.cancelPassword = function(user) {
        $scope.userpw = false;
    }

    $scope.pushPassword = function() {
        var pwchange = Restangular.one("setpassword", $scope.userpw.id);
        pwchange.customPOST({'password':$scope.userpw.password},'',{},{}).then(function(serverResponse) {
            console.log(serverResponse);
            $scope.userpw = false;
        });
    }

}]);
