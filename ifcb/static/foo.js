$(document).ready(function() {
    var width=640;
    var height=480;
    $.getJSON('/api/feed/format/json', function(r) {
	var center_column = $('#main').empty().append('<div/>').find('div:last').css('float','left');
	var right_column = $('#main').append('<div/>').find('div:last').css('float','right');
	$.each(r, function(ix, bin) {
	    if(ix < 7) {
		var images = []
		var mosaic_scale = ix == 0 ? 1.0 : 0.25;
		var roi_scale = 0.333 * mosaic_scale;
		var s_width = Math.floor(width * mosaic_scale);
		var s_height = Math.floor(height * mosaic_scale);
		var elt = ix == 0 ? center_column : right_column;
		for(page=1; page <= 30; page++) {
		    images.push('/api/mosaic/size/'+s_width+'x'+s_height+'/scale/'+roi_scale+'/page/'+page+'/pid/'+bin.lid+'.jpg');
		}
		$(elt).append('<div/><p class="bin_label">'+bin.lid+'</p>').find('div:last').imagePager(images, s_width, s_height);
	    }
	});
    });
});