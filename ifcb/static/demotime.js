$(document).ready(function() {
    // add a title
    var title = 'IFCB @ MVCO 2006-present'
    $('body').append('<h1>'+title+'</h1>');
    // create an invisible "workspace" element to hold data
    $('body').append('<div id="workspace"></div>')
	.find('#workspace').css('display','none')
	.data('mosaic_width',640)
	.data('mosaic_height',480)
	.data('roi_scale',0.333);
    // timeline thinks all timestamps are in the current locale, so we need
    // to fake that they're UTC
    function asUTC(date) {
	return new Date(date.getTime() - (date.getTimezoneOffset() * 60000));
    }
    // called when the user clicks on a date and wants to see the nearest bin
    function showNearest(date) {
	var ds = date.toISOString();
	$.getJSON('/api/feed/nearest/'+ds, function(r) { // find the nearest bin
	    $('#date_label').empty().append(r.date);
	    $('#workspace').data('selected_pid',r.pid);
	    $('#workspace').data('selected_date',r.date);
	    // now draw a multi-page mosaic
	    $('#mosaic_pager').trigger('drawMosaic');
	});
    }
    // add the timeline control
    $('body').append('<div id="timeline"></div>').find('div').timeline()
	.timeline_bind('timechange', function(timeline, r) {
	    // when the user is dragging the custom time bar, show the date/time
	    $('#date_label').empty().append(asUTC(r.time).toISOString());
	}).timeline_bind('timechanged', function(timeline, r) {
	    // correct tooltip to be in UTC
	    $('.timeline-customtime').attr('title',asUTC(r.time).toISOString());
	    // when the user is done dragging, show the nearest bin
	    showNearest(r.time);
	}).getTimeline(function(t) {
	    // when the user clicks on the data series, show the nearest bin
	    $('#timeline').bind('click', {timeline:t}, function(event) {
		// because timeline's select event is too coarse, we want to handle
		// every click. then we need to interrogate the timeline object itself,
		// hence the surrounding call to getTimeline
		var clickDate = event.data.timeline.clickDate;
		if(clickDate != undefined) {
		    // because timeline uses the current locale, we need to adjust for timezone offset
		    var utcClickDate = asUTC(clickDate);
		    showNearest(utcClickDate);
		}
	    });
	});
    // now load the data volume series
    console.log('loading data series...');
    // call the data volume API
    $.getJSON('/api/volume', function(volume) {
	// make a bar graph showing data volume
	var data = [];
	var minDate = new Date();
	var maxDate = new Date(0);
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
	    // track min/max date
	    if(start <= minDate) {
		minDate = start;
	    }
	    if(end >= maxDate) {
		maxDate = end;
	    }
	});
	// add a week to max date so that current time isn't squished over to the right
	maxDate = new Date(maxDate.getTime() + (86400000 * 7));
	// layout parameters accepted by showdata and passed to underlying widget
	var timeline_options = {
	    'width':  '100%',
	    'height': '150px',
	    'style': 'box',
	    'min': minDate,
	    'max': maxDate,
	    'showCustomTime': true,
	    'showNavigation': true,
	    'utc': true
	};
	// now tell the timeline plugin to draw it
	$('#timeline').trigger('showdata', [data, timeline_options]);
    });
    // our date label goes below the timeline
    $('body').append('<div id="date_label"></div>');
    // and the mosaic pager is below that
    $('body').append('<div id="mosaic_controls"></div>');
    // add some controls for changing the size of the mosaic
    var mosaic_sizes = [[640, 480], [800, 600], [1280, 720], [1280, 1280]];
    $('#mosaic_controls').append('Mosaic size: <span></span>').find('span:last')
	.radio(mosaic_sizes, function(size) {
 	    return size[0] + 'x' + size[1];
	}).bind('select', function(event, value) {
	    var width = value[0];
	    var height = value[1];
	    $('#workspace').data('mosaic_width', width)
		.data('mosaic_height', height);
	    $('#mosaic_pager').trigger('drawMosaic');
	});
    // add some controls for changing the roi scale in the mosaic
    var roi_scales = [15, 25, 33, 40, 66, 100];
    $('#mosaic_controls').append('ROI scaling: <span></span>').find('span:last')
	.radio(roi_scales, function(scale) {
	    return scale + '%';
	}).bind('select', function(event, value) {
	    $('#workspace').data('roi_scale', value/100);
	    $('#mosaic_pager').trigger('drawMosaic');
	});
    // now add the mosaic pager
    $('body').append('<div id="mosaic_pager"></div>').find('#mosaic_pager')
	.css('float','left')
	.bind('drawMosaic', function() { // on redraw
	    // make sure something is selected
	    var pid = $('#workspace').data('selected_pid');
	    if(pid == undefined) {
		return;
	    }
	    // get the selection and user preferred size/scale from the workspace
	    var roi_scale = $('#workspace').data('roi_scale'); // scaling factor per roi
	    var width = $('#workspace').data('mosaic_width'); // width of displayed mosaic
	    var height = $('#workspace').data('mosaic_height'); // height of displayed mosaic
	    // create the mosaic pager
	    $('#mosaic_pager').mosaicPager(pid, width, height, roi_scale)
		.bind('roi_click', function(event, roi_pid, roi_width, roi_height) {
		    console.log(roi_pid)
		    // we found it. now load the image and unscale it
		    $('#roi_image').empty()
		    // use grayLoadingImage from image_pager because it might take a while to load
			.grayLoadingImage(roi_pid+'.jpg', roi_width / roi_scale, roi_height / roi_scale)
			.append('<div></div>')
			.find('div:last')
			.css('clear','right')
			.css('float','right')
			.append('<span class="bin_label"><a href="'+roi_pid+'.html">'+roi_pid+'</a></span>')
			.append('<span> <a href="'+pid+'.xml">XML</a></span>')
			.append('<span> <a href="'+pid+'.rdf">RDF</a></span>')
			.end().find('.imagepager_frame').css('float','right');
		});
	});
    // now add a place to display the ROI image
    $('body').append('<div id="roi_image"></div>');
});
