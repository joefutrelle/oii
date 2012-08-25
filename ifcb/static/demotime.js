$(document).ready(function() {
    var title = 'MVCO data volume';
    $('body').append('<h1>'+title+'</h1>');
    $('body').append('<div></div>').find('div').timeline()
	.bind('dateHover', function(event, date) {
	    console.log('handling date hover '+date.toISOString());
	});
});
