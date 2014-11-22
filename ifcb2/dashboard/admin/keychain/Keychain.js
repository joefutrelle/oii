
ifcbAdmin.controller('KeyChainCtrl', ['$scope', 'Restangular', function ($scope, Restangular) {

    var baseUsers = Restangular.all('users');
    $scope.newkey = false;

    baseUsers.getList().then(function(serverResponse) {
        $scope.users = serverResponse;
    }, function(errorResponse) {
        console.log(errorResponse);
        $scope.alert = 'Unexpected ' + errorResponse.status.toString()
            + ' error while loading data from server.'
    });

    $scope.createKey = function() {
        $scope.newkey = true;
        $scope.keyview = false;
    }

    $scope.cancelKey = function() {
        $scope.newkey = false;
        $scope.keyview = false;
    }

    $scope.generateKey = function() {
        $scope.keyview = '12321-e3iuhe3dj-eij2oij-efea';
    }

}]);
