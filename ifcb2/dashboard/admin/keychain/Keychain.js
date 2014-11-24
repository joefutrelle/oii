
ifcbAdmin.controller('KeyChainCtrl', ['$scope', 'UserService', 'Restangular', function ($scope, UserService, Restangular) {

    var baseKeychain = Restangular.all('api_keys');
    $scope.users = UserService;
    $scope.newkey = false;

    function refreshKeychain() {
        baseKeychain.getList().then(function(serverResponse) {
            $scope.keychain = serverResponse;
        }, function(errorResponse) {
            console.log(errorResponse);
            $scope.alert = 'Unexpected ' + errorResponse.status.toString()
                + ' error while loading data from server.'
        });
    }

    refreshKeychain();

    $scope.createKey = function() {
        $scope.newkey = true;
        $scope.keyview = false;
    }

    $scope.cancelKey = function() {
        $scope.newkey = false;
        $scope.keyview = false;
    }

    $scope.generateKey = function(userid, name) {
        var pwchange = Restangular.one("genkey", userid);
        pwchange.customPOST({'name':name},'',{},{}).then(function(serverResponse) {
            $scope.keyview = serverResponse.token;
            refreshKeychain();
        });
    }

    $scope.revokeKey = function(key) {
        key.remove().then(function() {
            $scope.keychain = _.without($scope.keychain, key);
        });
    }

}]);
