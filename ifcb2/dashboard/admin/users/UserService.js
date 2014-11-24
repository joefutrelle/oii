
ifcbAdmin.service('UserService', ['Restangular', function (Restangular) {

    this.list = false;

    var baseUsers = Restangular.all('users');this.list = baseUsers.getList();
    this.post = baseUsers.post;

    this.new = function() {
        return {first_name:'', last_name:'', email:'', is_enabled:true, edit:true}
    }

}]);
