$(document).ready(function() {
    var title = 'MVCO data volume';
    var cache = {};
    function latest_bin(date, callback) {
	var ds = date.toISOString();
	var pid = cache[ds];
	if(pid == undefined) {
	    $.getJSON('/api/feed/nearest/'+ds, function(r) {
		pid = r.pid;
		cache[ds] = pid;
		callback(pid);
	    });
	} else {
	    callback(pid);
	}
    }
    $('body').append('<h1>'+title+'</h1>');
    $('body').append('<div></div>').find('div').timeline()
	.bind('dateClick', function(event, date) {
	    latest_bin(date, function(pid) {
		var images = []
		var mosaic_scale = 1.0;
		var roi_scale = 0.333 * mosaic_scale;
		var width = 600;
		var height = 480;
		var s_width = Math.floor(width * mosaic_scale);
		var s_height = Math.floor(height * mosaic_scale);
		for(page=1; page <= 30; page++) {
		    images.push('/api/mosaic/size/'+s_width+'x'+s_height+'/scale/'+roi_scale+'/page/'+page+'/pid/'+pid+'.jpg');
		}
		$('#mosaic_pager').empty().append('<div/><p class="bin_label">'+pid+'</p>')
		    .find('div:last').imagePager(images, s_width, s_height);
	    });
	});
    $('body').append('<div id="mosaic_pager"></div>');
});
