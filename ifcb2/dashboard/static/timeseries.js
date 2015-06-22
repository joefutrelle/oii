// ersatz history support for IE9, see #1857 for discussion
function historyPushState(state, pid, url) {
    if(!!(window.history && history.pushState)) {
	window.history.pushState(state, pid, url)
    } else {
	window.location.href = url;
    }
}

var $ws = undefined;

function timeseries_setup(e, pid, timeseries) {
    // internal function. params
    // e - element to add to
    // pid - (optional) initial pid to display
    // create an invisible "workspace" element to hold data
    $ws = $(e).append('<div id="workspace"></div>')
	.find('#workspace').css('display','none');
    $ws.data('show_roi_metadata',0);
    $ws.data('plot_type','xy');
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
	$('#date_label').empty()
	    .append(iso8601utcTime.replace(/....Z/,'Z'))
	    .css('margin-left',tts+'px');
    }
    function showBin(pid, pushHistory) {
	// remove any existing ROI image
	$('#roi_image').empty().css('display','none');
	// set the address for back button
	if(pushHistory == undefined || pushHistory) {
	    historyPushState({pid:pid, mosaic_state:{}}, pid, '/'+timeseries+'/dashboard/'+pid);
	}
	// update date label on timeline control
	$.getJSON(pid+'_short.json', function(r) { // need date information
	    $ws.data('selected_pid',r.pid);
	    // set the time markers accordingly
	    $('#date_label').empty().append(r.date); // FIXME no ms
	    $ws.data('selected_date',r.date);
	    var newCustomTime = asLocal(new Date(r.date));
	    $('#timeline').getTimeline(function(t) {
		console.log('setting custom time to '+newCustomTime);
		t.setCustomTime(newCustomTime);
		updateDateLabel(t);
	    });
	});
	// now draw a multi-page mosaic
	$('#bin_view').css('display','block').trigger('drawBinDisplay',[pid]);
    }
    // called when the user clicks on a date and wants to see the nearest bin
    function showNearest(date, pushHistory, callback) {
	var ds = date.toISOString();
	// FIXME need to specify time series
	$.getJSON('/'+timeseries+'/api/feed/nearest/'+ds, function(r) { // find the nearest bin
	    showBin(r.pid, pushHistory);
	    if(callback != undefined) {
		callback(r.pid);
	    }
	});
    }
    // add the timeline control
    $('#timeline').timeline()
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
    $('#timeline').collapsing('timeline',true);
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
	// add two years to max date so that current time isn't squished over to the right
	maxDate = new Date(maxDate.getTime() + (86400000 * 365 * 2));
	// subtract two years from min date so that current time isn't squished over to the left
	minDate = new Date(minDate.getTime() - (86400000 * 365 * 2));
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
	    showBin(pid, false);
	} else {
	    showNearest(new Date(), false, function(nearest) {
		historyPushState({pid:nearest, mosaic_state:{}}, nearest, '/'+timeseries);
	    });
	}
	$('#timeline').trigger('showdata', [data, timeline_options]);
    });
    $('#title_content').collapsing('title',true);
    // the ROI image is closable and initially hidden
    $('#roi_image').closeBox().css('display: none');
    function showRoi(evt, roi_pid) {
	$.getJSON(roi_pid+'.json', function(r) {
	    // use grayLoadingImage from image_pager to display the ROI
	    var roi_width = r.height; // note that h/w is swapped (90 degrees rotated)
	    var roi_height = r.width; // note that h/w is swapped (90 degrees rotated)
	    console.log('collapse state is '+$ws.data('show_roi_metadata'))
	    $('#roi_image').empty()
		.closeBox()
		.css('display','inline-block')
		.target_image(roi_pid, roi_width, roi_height)
		.append('<br><div class="roi_info bin_label"></div>').find('.roi_info')
		.append('<a href="'+roi_pid+'.html">'+roi_pid+'</a> ')
		.append(' (<a href="'+roi_pid+'.xml">XML</a> ')
		.append('<a href="'+roi_pid+'.rdf">RDF</a>)').end()
		.append('<div><div class="target_metadata"></div></div>')
		.find('.target_metadata')
		.target_metadata(roi_pid)
		.collapsing('metadata',$ws.data('show_roi_metadata'))
		.bind('collapse_state', function(event, s) {
		    console.log('setting collapse state to '+s);
		    $ws.data('show_roi_metadata', s);
		}).end()
		.find('.target_image').css('float','right');
	});
    }
    // and the resizable bin view is below that
    // e.g., containing the mosaic or plot
    $('#bin_view')
	.closeBox()
	.resizableBinView(timeseries)
	.bind('roi_click', function(event, roi_pid) {
	    showRoi(event, roi_pid)
	}).bind('goto_bin', function(event, bin_pid) {
	    showBin(bin_pid);
	});
    // handle popstate
    window.onpopstate = function(event) {
	console.log(event);
	if(event.state) {
	    if(event.state.pid) {
		showBin(event.state.pid, false);
	    }
	    if(event.state.mosaic_state) {
		$('#bin_view').trigger('restoreState', event.state.mosaic_state);
	    }
	}
    };
}
(function($) {
    $.fn.extend({
	timeseries: function(bin_pid, timeseries) {
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		timeseries_setup($this, bin_pid, timeseries);
	    });//each in bin_page
	}//bin_page
    });//$.fn.extend
})(jQuery);//end of plugin
