
/*
By breaking API calls out into services,
we avoid hitting the endpoint over and over again
each time we change views in the application.
(https://docs.angularjs.org/guide/services)

The service is where most business logic should be packed.
More and more will be moved as we go.
*/

ifcbAdmin.service('TimeSeriesService', ['Restangular', function (Restangular) {

    var baseTimeSeries = Restangular.all('time_series');
    this.list = baseTimeSeries.getList();
    this.post = baseTimeSeries.post;

    this.new = function() {
        return {label:'',description:'',data_dirs:[{path:'',product_type:'raw'}],edit:'true'}
    }

}]);

ifcbAdmin.service('InstrumentService', ['Restangular', function (Restangular) {

    var baseInstruments = Restangular.all('instruments');

    this.list = baseInstruments.getList();
    this.post = baseInstruments.post;

    this.new = function() {
        return {name:'',data_path:'',edit:true}
    }

}]);


ifcbAdmin.service('RoleService', ['Restangular', function (Restangular) {

    this.list = Restangular.all('roles').getList();

}]);
