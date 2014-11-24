

// users controller
ifcbAdmin.controller('UserCtrl', ['$scope', 'UserService', 'RoleService', 'Restangular', function ($scope, UserService, RoleService, Restangular) {

    // initialize local scope
    $scope.newuser = false;
    $scope.users= UserService;
    $scope.editing = {};

    // save user to server
    $scope.saveUser = function(user) {
        // user will log in with email + password
        // so here username will always be set to email address
        user.username = user.email;
        if(user.id) {
            // user already exists on server. update.
            // copy "now editing" object to user object
            angular.copy($scope.editing[user.id], user);
            // save to server
            UserService.update(user).then(function(serverResponse) {
                // successful response. delete from "now editing" list
                delete $scope.editing[user.id];
                $scope.alert = null;
            }, function(serverResponse) {
                // failed! throw error
                console.log(serverResponse);
                $scope.alert = 'Unexpected ' + errorResponse.status.toString()
                    + ' error while loading data from server.';
            });
        } else {
            // new user. post to server.
            UserService.save(user).then(function(serverResponse) {
                // copy server response to scope object
                $scope.users.list.push(serverResponse);
                $scope.newuser = false;
                $scope.alert = null;
            }, function(serverResponse) {
                // failed! throw error
                console.log(serverResponse);
                $scope.alert = 'Unexpected ' + errorResponse.status.toString()
                    + ' error while loading data from server.';
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
            // cancel edit on existing user
            delete $scope.editing[user.id];
        } else {
            // canel edit on new user
            $scope.newuser = false;
        }
    }

    $scope.editUser = function(user) {
        // copy user into "now editing"
        $scope.editing[user.id] = {}
        angular.copy(user, $scope.editing[user.id]);
    }

    $scope.isEditing = function(user) {
        if (user.id in $scope.editing) {
            return true
        } else {
            return false
        }
    }

    // toggle user status
    $scope.toggleUser = function(user) {
        tmpuser = user.clone();
        tmpuser.is_enabled = !tmpuser.is_enabled;
        UserService.update(tmpuser).then(function(serverResponse) {
            user.is_enabled = !user.is_enabled;
        }, function(serverResponse) {
            // failed! throw error
            console.log(serverResponse);
            $scope.alert = 'Unexpected ' + errorResponse.status.toString()
                + ' error while loading data from server.';
        });
    }

    $scope.setPassword = function(user) {
        $scope.userpw = user;
    }

    $scope.cancelPassword = function(user) {
        $scope.userpw = false;
    }

    $scope.pushPassword = function() {
        UserService.updatePassword($scope.userpw, $scope.userpw.password).then(function(serverResponse) {
            console.log(serverResponse);
            $scope.userpw = false;
        }, function(serverResponse) {
            // failed! throw error
            console.log(serverResponse);
            $scope.alert = 'Unexpected ' + errorResponse.status.toString()
                + ' error while loading data from server.';
        });
    }

}]);
