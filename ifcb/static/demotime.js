$(document).ready(function() {
    // add a title
    var title = 'IFCB @ MVCO 2006-present'
    $('body').append('<h1>'+title+'</h1><div id="workspace"></div>')
	.find('#workspace').css('display','none')
	.data('mosaic_width',640)
	.data('mosaic_height',480)
	.data('roi_scale',0.333);
    function showNearest(date) {
	var ds = date.toISOString();
	$.getJSON('/api/feed/nearest/'+ds, function(r) { // find the nearest bin
	    console.log(JSON.stringify(r)); // FIXME need the date
	    $('#date_label').empty().append(r.date);
	    $('#workspace').data('selected_pid',r.pid);
	    $('#workspace').data('selected_date',r.date);
	    // now draw a multi-page mosaic
	    $('#mosaic_pager').trigger('drawMosaic');
	});
    }
    // add the timeline control
    $('body').append('<div id="timeline"></div>').find('div').timeline()
	/*
	.bind('dateHover', function(event, date, clientX) { // on hover, show the date
	    $('#date_label').empty().append(date.toISOString());
	    $('#date_label').css('margin-left',clientX);
	})
	.bind('dateClick', function(event, date, clientX) { // on click,
	});
	*/
	.timeline_bind('timechange', function(timeline, r) {
	    $('#date_label').empty().append(r.time.toISOString());
	}).timeline_bind('timechanged', function(timeline, r) {
	    showNearest(r.time);
	}).getTimeline(function(t) {
	    // because timeline's select event is too coarse, we want to handle
	    // every click. then we need to interrogate the timeline object itself,
	    // hence the surrounding call to getTimeline
	    $('#timeline').bind('click', {timeline:t}, function(event) {
		var clickDate = event.data.timeline.clickDate;
		// the call to "get selection" ensures that we clicked on data
		// and not on a gap.
		$.each(t.getSelection(), function(ix, s) {
		    $('#date_label').empty().append(clickDate.toISOString());
		    showNearest(clickDate);
		});
	    });
	});
    ;
    // now load the data volume series
    console.log('loading data series...');
    $.getJSON('/api/volume', function(volume) {
	// make a bar graph showing data volume
	var data = [];
	$.each(volume, function(ix, day_volume) {
	    // for each day/volume record, make a bar
	    // get the volume data for that day
	    var bin_count = day_volume.bin_count;
	    var date = day_volume.day; // FIXME key should be "date"
	    var gb = day_volume.gb; // FIXME currently ignored
	    // create a one-day time interval
	    var year = date.split('-')[0];
	    var month = date.split('-')[1];
	    var day = date.split('-')[2];
	    var start = new Date(year, month-1, day)
	    var end = new Date(year, month-1, day);
	    end.setHours(end.getHours() + 24);
	    // create a bar. here we need to scale GB to > 1px/GB or else the bars'll be tiny
	    var height = Math.round(gb * 15);
	    var style = 'height:' + height + 'px;'
	    var color = '#ff0000';
	    style = 'height:' + height + 'px;' +
		'margin-bottom: -25px;'+
		'background-color: ' + color + ';'+
		'border: 1px solid ' + color + ';';
	    var bar = '<div class="bar" style="' + style + '" ' +
		' title="'+gb.toFixed(2)+'GB"></div>';
	    var item = {
		'group': 'bytes/day', // "Group" is displayed on the left as a label
		'start': start,
		'end': end,
		'content': bar
	    };
	    // we're done with one bar
	    data.push(item);
	});
	// layout parameters accepted by showdata and passed to underlying widget
	var timeline_options = {
	    'width':  '100%',
	    'height': '150px',
	    'style': 'box',
	    'showCustomTime': true,
	    'showNavigation': true
	};
	// now tell the timeline plugin to draw it
	$('#timeline').trigger('showdata', [data, timeline_options]);
    });
    // our date label goes below the timeline
    $('body').append('<div id="date_label"></div>');
    // and the mosaic pager is below that
    $('body').append('<div id="mosaic_controls"></div>');
    var mosaic_sizes = [[640,480],[800,600],[1280,720],[1280,1280]];
    $.each(mosaic_sizes, function(ix, size) {
	var width = size[0];
	var height = size[1];
	$('#mosaic_controls').append('<a>'+width+'x'+height+'</a>')
	    .find('a:last')
	    .button()
	    .click(function() {
		$('#workspace').data('mosaic_width', width)
		    .data('mosaic_height', height);
		$('#mosaic_pager').trigger('drawMosaic');
	    });
    });
    var magnifications = [10, 25, 33, 50, 66, 75, 100];
    $.each(magnifications, function(ix, magnification) {
	$('#mosaic_controls').append('<a>'+magnification+'%</a>')
	    .find('a:last')
	    .button()
	    .click(function() {
		$('#workspace').data('roi_scale', magnification/100);
		$('#mosaic_pager').trigger('drawMosaic');
	    });
    });
    $('body').append('<div id="mosaic_pager"></div>').find('#mosaic_pager')
	.bind('drawMosaic', function() {
	    var pid = $('#workspace').data('selected_pid');
	    if(pid == undefined) {
		return;
	    }
	    var date = $('#workspace').data('selected_date');
	    var roi_scale = $('#workspace').data('roi_scale'); // scaling factor per roi
	    var width = $('#workspace').data('mosaic_width'); // width of displayed mosaic
	    var height = $('#workspace').data('mosaic_height'); // height of displayed mosaic
	    // put 30 pages on the pager, just in case it's a huge bin
	    var images = [];
	    for(var page=1; page <= 30; page++) {
		var url = '/api/mosaic/size/'+width+'x'+height+'/scale/'+roi_scale+'/page/'+page+'/pid/'+pid+'.jpg';
		images.push(url);
	    }
	    // create an image pager
	    $('#mosaic_pager').empty().append('<div/><p class="bin_label">'+pid+'</p>')
		.find('div:last').imagePager(images, width, height)
		.bind('change', function(event, image_href) {
		    console.log('user paged to '+image_href);
		}).delegate('.page_image', 'click', function(event) {
		    // figure out where the click was
		    var clickX = event.pageX - $(this).offset().left;
		    var clickY = event.pageY - $(this).offset().top;
		    console.log('user clicked at '+clickX+','+clickY);
		    // FIXME now figure out which ROI the user clicked on
		});
	});
});
