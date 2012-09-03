function timeseries_add(e, pid) {
    // internal function. params
    // e - element to add to
    // pid - (optional) initial pid to display
    // create an invisible "workspace" element to hold data
    $(e).append('<div id="workspace"></div>')
	.find('#workspace').css('display','none');
    // timeline thinks all timestamps are in the current locale, so we need
    // to fake that they're UTC
    function asUTC(date) {
	return new Date(date.getTime() - (date.getTimezoneOffset() * 60000));
    }
    function showMosaic(pid, pushHistory) {
	// now draw a multi-page mosaic
	$('#mosaic_pager').trigger('drawMosaic',[pid]);
	// set the address for back button
	if(pushHistory == undefined || pushHistory) {
	    window.history.pushState(pid, pid, '/api/timeseries/pid/'+pid);
	}
    }
    // called when the user clicks on a date and wants to see the nearest bin
    function showNearest(date) {
	var ds = date.toISOString();
	$.getJSON('/api/feed/nearest/'+ds, function(r) { // find the nearest bin
	    $('#date_label').empty().append(r.date);
	    $('#workspace').data('selected_pid',r.pid);
	    $('#workspace').data('selected_date',r.date);
	    showMosaic(r.pid);
	});
    }
    // add the timeline control
    $(e).append('<div id="timeline"></div>').find('#timeline').timeline()
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
    $(e).append('<div id="date_label"></div>');
    // now add a place to display the ROI image
    $(e).append('<div id="roi_image"></div>');
    // and the mosaic pager is below that
    $(e).append('<div id="mosaic_pager"></div>').find('#mosaic_pager')
	.css('float','left')
	.resizableMosaicPager()
	.bind('roi_click', function(event, roi_pid) {
	    // we found it. now determine ROI image dimensions by hitting the ROI endpoint
	    $.getJSON(roi_pid+'.json', function(r) {
		// use grayLoadingImage from image_pager to display the ROI
		var roi_width = r.height; // note that h/w is swapped (90 degrees rotated)
		var roi_height = r.width; // note that h/w is swapped (90 degrees rotated)
		$('#roi_image').empty()
		    .grayLoadingImage(roi_pid+'.jpg', roi_width, roi_height)
		    .click(function() {
			// if user clicks on roi image, go to roi page
			window.location.href = roi_pid + '.html';
		    }).css('float','right')
		    .css('text-align','right')
		    .append('<div class="roi_info bin_label"></div>').find('.roi_info')
		    .append('<a href="'+roi_pid+'.html">'+roi_pid+'</a> ')
		    .append('<a href="'+roi_pid+'.xml">XML</a> ')
		    .append('<a href="'+roi_pid+'.rdf">RDF</a>').end()
		    .find('.imagepager_frame').css('float','right');
	    });
	});
    // if a pid is selected, show it
    if(pid != undefined) {
	showMosaic(pid, false);
    }
    // handle popstate
    window.onpopstate = function(event) {
	if(event.state != undefined) {
	    console.log(event.state);
	    showMosaic(event.state, false);
	}
    };
}
(function($) {
    $.fn.extend({
	timeseries: function(bin_pid) {
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		timeseries_add($this, bin_pid);
	    });//each in bin_page
	}//bin_page
    });//$.fn.extend
})(jQuery);//end of plugin
