

// users controller
ifcbAdmin.controller('UserCtrl', ['$scope', '$window', 'UserService', 'RoleService', 'Restangular', function ($scope, $window, UserService, RoleService, Restangular) {

    // initialize local scope
    $scope.alert = null;
    $scope.restore = {};
    $scope.rolesByName = {}

    UserService.list.then(function(r) {
	$scope.users = r;
    });
    RoleService.list.then(function(r) {
	$scope.roles = r;
	$.each(r, function(ix, role) {
	    $scope.rolesByName[role.name] = {
		'id': role.id,
		'name': role.name,
	    };
	});
    });

    // create new user
    $scope.addNewUser = function() {
	var user = UserService.new();
	$scope.users.push(user);
	$scope.editUser(user);
	return true;
    }

    $scope.deleteUser = function(user) {
	var delete_user = Restangular.one("delete_user", user.id);
	$scope.alert = "Deleting "+user.first_name+" "+user.last_name+" ...";
	delete_user.customPOST().then(function() {
	    $window.location.reload();
	});
    }

    $scope.editUser = function(user) {
        // copy user into "now editing"
	$scope.restore[user.id] = {}
        angular.copy(user, $scope.restore[user.id]);
	user.edit = true;
    }

    $scope.cancelUser = function(user) {
	if(user.id && !$.isEmptyObject($scope.restore)) {
	    angular.copy($scope.restore[user.id], user);
	    delete $scope.restore[user.id];
	    user.edit = false;
	} else {
	    $scope.users = _.without($scope.users, user);
	}
    }

    // save user to server
    $scope.saveUser = function(user) {
        // user will log in with email + password
        // so here username will always be set to email address
        user.username = user.email;
        if(user.id) {
	    var patch_user = Restangular.one("patch_user", user.id);
	    patch_user.customPOST(user).then(function() {
                // successful response.
                delete user.edit;
		delete $scope.restore[user.id];
		console.log('SUCCEEDED in patching user');
                $scope.alert = null;
            }, function(r) {
		console.log('FAILED to patch user');
		console.log(r);
	    });
        } else {
	    UserService.post(user).then(function(r) {
		angular.copy(r, user);
	    });
	}
    }

    $scope.enableUser = function(user, flag) {
	user.is_enabled = flag;
	$scope.saveUser(user);
    }

    $scope.isAdmin = function(user) {
	var isAdmin = false;
	if(user.roles.length > 0) {
	    $.each(user.roles, function(ix,r) {
		if(r.name=='Admin') {
		    isAdmin = true;
		}
	    });
	}
	return isAdmin;
    }

    $scope.promoteUser = function(user) {
	var promote_user = Restangular.one("promote_user", user.id);
	promote_user.customPOST(user).then(function() {
	    user.roles = [{
		'name': 'Admin'
	    }]
	    console.log('user is now admin');
	});
	return true;
    }

    $scope.demoteUser = function(user) {
	var demote_user = Restangular.one("demote_user", user.id);
	demote_user.customPOST(user).then(function() {
	    user.roles = [];
	    console.log('user is now not admin');
	});
	return true;
    }

    $scope.setPassword = function(user) {
        $scope.userpw = user;
    }

    $scope.cancelPassword = function(user) {
        $scope.userpw = false;
    }

    $scope.pushPassword = function() {
	var pw_user = $scope.userpw;
	var pw_password = $scope.userpw.password;
	var pwchange = Restangular.one("setpassword", pw_user.id);
	pwchange.customPOST({'password':pw_password},'',{},{}).then(function(serverResponse) {
            console.log(serverResponse);
            $scope.userpw = false;
        }, function(serverResponse) {
            // failed! throw error
            console.log(serverResponse);
            $scope.alert = 'Unexpected ' + errorResponse.status.toString()
                + ' error while loading data from server.';
        });
    }
$scope.$on('$locationChangeStart', function( event ) {
	if($.isEmptyObject($scope.restore)) {
		return;
	}
	$.each($scope.users, function(ix, u) {
		if(u.edit) {
			$scope.cancelUser(u);
			u.edit = false;
		}
	});
});
}]);
