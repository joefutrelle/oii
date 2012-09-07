(function($) {
    $.fn.extend({
	closeBox: function() {
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		$this.prepend('<a class="close"></a>').find('a:first')
		    .bind('click', function() {
			$this.css('display','none');
		    });
	    });// each in closeBox
	}//closeBox
    });//$.fn.extend
})(jQuery);//end of plugin

function timeseries_add(e, pid, timeseries) {
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
    function asLocal(date) {
	return new Date(date.getTime() + (date.getTimezoneOffset() * 60000));
    }
    function updateDateLabel(timeline) {
	var customTime = timeline.getCustomTime();
	var iso8601utcTime = asUTC(customTime).toISOString();
	var tts = timeline.timeToScreen(customTime);
	$('#date_label').empty().append(iso8601utcTime)
	    .css('margin-left',tts+'px');
    }
    function showMosaic(pid, pushHistory) {
	// remove any existing ROI image
	$('#roi_image').empty().css('display','none');
	// set the address for back button
	if(pushHistory == undefined || pushHistory) {
	    window.history.pushState({pid:pid, mosaic_state:{}}, pid, '/'+timeseries+'/dashboard/pid/'+pid);
	}
	// update date label on timeline control
	$.getJSON(pid+'_short.json', function(r) { // need date information
	    $('#workspace').data('selected_pid',r.pid);
	    // set the time markers accordingly
	    $('#date_label').empty().append(r.date); // FIXME no ms
	    $('#workspace').data('selected_date',r.date);
	    var newCustomTime = asLocal(new Date(r.date));
	    $('#timeline').getTimeline(function(t) {
		console.log('setting custom time to '+newCustomTime);
		t.setCustomTime(newCustomTime);
		updateDateLabel(t);
	    });
	});
	// now draw a multi-page mosaic
	$('#mosaic_pager').css('display','block').trigger('drawMosaic',[pid]);
/*
	    .bind('state_change', function(event, s) {
		var stateString = 'p'+s.pageNumber+'s'+s.width+'x'+s.height+'s'+s.roi_scale;
		console.log('mosaic state string = '+stateString);
		if(false && s.pageNumber > 1) { // FIXME currently disabled
		    history.pushState({pid:pid, mosaic_state:s}, pid, '/'+timeseries+'/dashboard/pid/'+pid+'#'+stateString);
		}
	    });
*/
    }
    // called when the user clicks on a date and wants to see the nearest bin
    function showNearest(date) {
	var ds = date.toISOString();
	// FIXME need to specify time series
	$.getJSON('/'+timeseries+'/api/feed/nearest/'+ds, function(r) { // find the nearest bin
	    showMosaic(r.pid);
	});
    }
    // add the timeline control
    $(e).append('<div class="major"><div class="h2">Data volume by day</div><br><div id="timeline"></div></div>').find('#timeline').timeline()
	.timeline_bind('timechange', function(timeline, r) {
	    // when the user is dragging the custom time bar, show the date/time
	    updateDateLabel(timeline);
	}).timeline_bind('timechanged', function(timeline, r) {
	    // correct tooltip to be in UTC
	    $('.timeline-customtime').attr('title',asUTC(r.time).toISOString());
	    // when the user is done dragging, show the nearest bin
	    showNearest(r.time);
	}).timeline_bind('rangechanged', function(timeline, r) {
	    updateDateLabel(timeline);
	}).timeline_bind('rangechange', function(timeline, r) {
	    updateDateLabel(timeline);
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
    $.getJSON('/'+timeseries+'/api/volume', function(volume) {
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
	// add a year to max date so that current time isn't squished over to the right
	maxDate = new Date(maxDate.getTime() + (86400000 * 365));
	// subtract a year to max date so that current time isn't squished over to the right
	minDate = new Date(minDate.getTime() - (86400000 * 365));
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
	// if a pid is selected, show it
	if(pid != undefined) {
	    showMosaic(pid, false);
	} else {
	    showNearest(new Date());
	}
	$('#timeline').trigger('showdata', [data, timeline_options]);
    });
    $('#title').closeBox();
    // our date label goes below the timeline
    $(e).append('<div id="date_label" class="major"></div>');
    // now add a place to display the ROI image
    $(e).append('<div id="roi_image" class="major target_image"></div>').find('div:last')
	.closeBox()
	.css('display','none');
    // and the mosaic pager is below that
    $(e).append('<div id="mosaic_pager" class="major"></div>').find('#mosaic_pager')
	.closeBox()
	.resizableMosaicPager()
	.bind('roi_click', function(event, roi_pid) {
	    // we found it. now determine ROI image dimensions by hitting the ROI endpoint
	    $.getJSON(roi_pid+'.json', function(r) {
		// use grayLoadingImage from image_pager to display the ROI
		var roi_width = r.height; // note that h/w is swapped (90 degrees rotated)
		var roi_height = r.width; // note that h/w is swapped (90 degrees rotated)
		$('#roi_image').empty()
		    .closeBox()
		    .css('display','inline-block')
		    .target_image(roi_pid, roi_width, roi_height)
		    .append('<br><div class="roi_info bin_label"></div>').find('.roi_info')
		    .append('<a href="'+roi_pid+'.html">'+roi_pid+'</a> ')
		    .append(' (<a href="'+roi_pid+'.xml">XML</a> ')
		    .append('<a href="'+roi_pid+'.rdf">RDF</a>)').end()
		    .append('<div><div class="target_metadata"></div></div>')
		    .find('.target_metadata').target_metadata(roi_pid).collapsing('metadata').end()
		    .find('.target_image').css('float','right');
	    });
	});
    // handle popstate
    window.onpopstate = function(event) {
	console.log(event);
	if(event.state) {
	    if(event.state.pid) {
		showMosaic(event.state.pid, false);
	    }
	    if(event.state.mosaic_state) {
		$('#mosaic_pager').trigger('restoreState', event.state.mosaic_state);
	    }
	}
    };
}
(function($) {
    $.fn.extend({
	timeseries: function(bin_pid, timeseries) {
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		timeseries_add($this, bin_pid, timeseries);
	    });//each in bin_page
	}//bin_page
    });//$.fn.extend
})(jQuery);//end of plugin
