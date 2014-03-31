
function TimeSeries($scope, $http) {
    $http.get('/admin/api/v1.0/timeseries')
        .success(function(data) {
            $scope.timeseries = data.timeseries;
            console.log(data);
        });
}
