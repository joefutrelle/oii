function elementInViewport(el) {
    var top = el.offsetTop;
    var left = el.offsetLeft;
    var width = el.offsetWidth;
    var height = el.offsetHeight;

    while(el.offsetParent) {
	el = el.offsetParent;
	top += el.offsetTop;
	left += el.offsetLeft;
    }

    return (
    top >= window.pageYOffset &&
    left >= window.pageXOffset &&
	    (top + height) <= (window.pageYOffset + window.innerHeight) &&
	    (left + width) <= (window.pageXOffset + window.innerWidth)
    );
}
function loadImages() {
    $.each($('#main').find('.roi_image_unloaded'),function(ix,elt) {
	if(elementInViewport(elt)) {
	    img_src = $(elt).data('img_src');
	    console.log(img_src+' in viewport');
	    $(elt).find('a').append('<img src="'+img_src+'" width="50%" alt="'+img_src+'">');
	    $(elt).removeClass('roi_image_unloaded').addClass('roi_image');
	    $(elt).css('width','auto');
	    $(elt).css('height','auto');
	}
    });
}
function showit() {
    var class_label = $('#class_select').val();
    var threshold = $('#threshold').slider('value') / 100.0;
    var startDate = $('#date_range').data('startDate');
    var endDate = $('#date_range').data('endDate');
    $('#images').empty().append('please wait...');
    $.getJSON('/mvco/api/autoclass/rois_of_class/'+class_label+'/threshold/'+threshold+'/start/'+startDate+'/end/'+endDate, function(r) {
	$('#images').empty();
	$.each(r, function(ix, roi_pid) {
	    if(ix < 1000) {
		$('#images').append('<div style="display:inline-block;width:200px;height:200px"><a href="'+roi_pid+'.html" target="_blank"></a></div>')
		    .find('div:last')
		    .addClass('roi_image_unloaded')
		    .data('img_src',roi_pid+'.png');
	    }
	});
	loadImages();
    });
}
function showThreshVal() {
    $('#thresh_val').empty().append('' + $('#threshold').slider('value') / 100.0);
}
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
	var theRange = timeline.getVisibleChartRange()
	var startDate = asUTC(theRange.start).toISOString();
	var endDate = asUTC(theRange.end).toISOString();
	$('#date_range').data('startDate',startDate).data('endDate',endDate);
	$('#date_range').empty().append(startDate + ' - ' + endDate);
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
    $('#main').append('<div id="date_range" class="major"></div>');
    $('#gb_day_timeline').gb_day_timeline('mvco');
    $('#main').append('<select id="class_select"></select>');
    $('#main').append('<div style="display: inline-block; width: 300px" id="threshold">').find('#threshold')
	.slider({
	    min: 1,
	    max: 99,
	    value: 99,
	    change: function () {
		showThreshVal();
	    }
	});
    $('#main').append('<span id="thresh_val"></span>');
    $('#main').append('<div>Go</div>').find('div:last').button().click(function() {
	showit();
    });
    $('#main').append('<div id="images"></div>')
    $.getJSON('/mvco/api/autoclass/list_classes', function(r) {
	$.each(r, function(ix, class_label) {
	    $('#class_select').append('<option value="'+class_label+'">'+class_label+'</option>');
	});
	showThreshVal();
    });
    $(window).scroll(loadImages);
});