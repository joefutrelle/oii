$(document).ready(function() {
    var width=640;
    var height=480;
    $.getJSON('/api/feed/format/json', function(r) {
	var center_column = $('#main').empty().append('<div/>').find('div:last').css('float','left');
	var right_column = $('#main').append('<div/>').find('div:last').css('float','right');
	$.each(r, function(ix, bin) {
	    var images = []
	    for(page=1; page <= 30; page++) {
		images.push('/api/mosaic/size/'+width+'x'+height+'/scale/0.333/page/'+page+'/pid/'+bin.lid+'.jpg');
	    }
	    if(ix == 0) {
		$(center_column).append('<div/>').find('div').imagePager(images, width, height);
	    } else {
		$(right_column).append('<div/><br/>').find('div:last').imagePager(images, Math.floor(width/4), Math.floor(height/4));
	    }
	});
    });
});