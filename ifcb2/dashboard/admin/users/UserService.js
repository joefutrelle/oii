
ifcbAdmin.service('UserService', ['Restangular', function (Restangular) {

    var baseUsers = Restangular.all('users');
    var thisUserService = this;

    // fetch initial user list
    baseUsers.getList().then(function(serverResponse) {
        thisUserService.list = serverResponse;
    }, function(errorResponse) {
        console.log(errorResponse);
        thisUserService.alert = 'Unexpected ' + errorResponse.status.toString()
            + ' error while loading data from server.'
    });

    // create a new, unsaved user object
    this.new = function() {
        return {first_name:'', last_name:'', email:'', is_enabled:true}
    }

    // save a user object to the server and return a promise
    this.save = function(user) {
        return baseUsers.post(user);
    }

    // update a user object on the server and return a promise
    this.update = function(user) {
        return user.patch();
    }

}]);
