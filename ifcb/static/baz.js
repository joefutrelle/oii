function gb_day_timeline_add(e, timeseries) {
    // internal function. params
    // e - element to add to
    // class_label - class label
    // create an invisible "workspace" element to hold data
    $ws = $(e).append('<div id="workspace"></div>')
	.find('#workspace').css('display','none');
    // timeline thinks all timestamps are in the current locale, so we need
    // to fake that they're UTC
    function asUTC(date) {
	return new Date(date.getTime() - (date.getTimezoneOffset() * 60000));
    }
    function asLocal(date) {
	return new Date(date.getTime() + (date.getTimezoneOffset() * 60000));
    }
    function updateRange(timeline) {
	//var theTime = timeline.getXx()
	//var theISOTime = asUTC(theTime).toISOString();
    }
    // add the timeline control
    $(e).append('<div class="major"><div class="h2">Data volume by day</div><br><div id="timeline"></div></div>').find('#timeline').timeline()
        .timeline_bind('rangechanged', function(timeline, r) {
	    updateRange(timeline);
	}).timeline_bind('rangechange', function(timeline, r) {
	    updateRange(timeline);
	});
    // now load the data volume series
    console.log('loading data series...');
    // call the data volume API
    $.getJSON('/'+timeseries+'/api/volume', function(volume) {
	console.log('data loaded.');
	// make a bar graph showing data volume
	var data = [];
	var minDate = new Date();
	var maxDate = new Date(0);
	$.each(volume, function(ix, day_volume) {
	    // for each day/volume record, make a bar
	    // get the volume data for that day
	    var gb = day_volume.gb;
	    var date = day_volume.day; // FIXME key should be "date"
	    // create a one-day time interval
	    var year = date.split('-')[0];
	    var month = date.split('-')[1];
	    var day = date.split('-')[2];
	    var start = new Date(year, month-1, day)
	    var end = new Date(year, month-1, day);
	    end.setHours(end.getHours() + 24);
	    var height = Math.round(gb * 15);
	    var color = '#ff0000';
	    var style = 'height:' + height + 'px;' +
		'margin-bottom: -25px;'+
		'background-color: ' + color + ';'+
		'border: 1px solid ' + color + ';';
	    var bar = '<div class="bar" style="' + style + '" ' +
		' title="'+gb+'GB"></div>';
	    var item = {
		'group': 'GB/day', // "Group" is displayed on the left as a label
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
	    'showNavigation': true,
	    'utc': true
	};
	// now tell the timeline plugin to draw it
	$('#timeline').trigger('showdata', [data, timeline_options]);
    });
}
(function($) {
    $.fn.extend({
	gb_day_timeline: function(timeseries) {
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		gb_day_timeline_add($this, timeseries);
	    });//each in bin_page
	}//bin_page
    });//$.fn.extend
})(jQuery);//end of plugin
$(document).ready(function() {
    $('#main').append('<div id="gb_day_timeline">');
    $('#gb_day_timeline').gb_day_timeline('mvco');
});