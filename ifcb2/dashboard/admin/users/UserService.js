
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

    // creates a new, unsaved user object
    this.new = function() {
        return {first_name:'', last_name:'', email:'', is_enabled:true}
    }

    // saves a user object to the server
    this.save = function(user) {

    }

}]);
