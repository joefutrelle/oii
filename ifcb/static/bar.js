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
	    $(elt).find('a').append('<img src="'+img_src+'" alt="'+img_src+'">');
	    $(elt).removeClass('roi_image_unloaded').addClass('roi_image');
	    $(elt).css('width','auto');
	    $(elt).css('height','auto');
	}
    });
}
function showit() {
    var class_label = $('#class_select').val();
    var threshold = $('#threshold').slider('value') / 100.0;
    var startDate = $('#date_range').data('startDate').toISOString();
    var endDate = $('#date_range').data('endDate').toISOString();
    $('#images').empty().append('please wait...');
    $.getJSON('/mvco/api/autoclass/rois_of_class/'+class_label+'/threshold/'+threshold+'/start/'+startDate+'/end/'+endDate, function(r) {
	$('#images').empty();
	$.each(r, function(ix, roi_pid) {
	    if(ix < 1000) {
		$('#images').append('<div style="display:inline-block;width:200px;height:200px"><a href="'+roi_pid+'.html"></a></div>')
		    .find('div:last')
		    .addClass('roi_image_unloaded')
		    .data('img_src',roi_pid+'.png');
	    }
	});
	loadImages();
    });
}
var EPOCH = (new Date(2006,0,1)).getTime();
var NOW = (new Date()).getTime();
$(document).ready(function() {
    $('#main').append('<select id="class_select"></select>');
    $('#main').append('<div style="display: inline-block; width: 300px" id="threshold">').find('#threshold')
	.slider({
	    min: 1,
	    max: 99,
	    value: 99,
	    change: function () {
		$('#thresh_val').empty().append('' + $('#threshold').slider('value') / 100.0);
		showit();
	    }
	});
    $('#main').append('<span id="thresh_val"></span>');
    $('#main').append('<div style="display: inline-block; width: 300px" id="date_range">').find('#date_range')
	.slider({
	    range: true,
	    min: 1,
	    max: 1000,
	    values: [800, 900],
	    change: function() {
		var values = $('#date_range').slider('values');
		var startDate = new Date(EPOCH + ((values[0] / 1000) * (NOW - EPOCH)));
		var endDate = new Date(EPOCH + ((values[1] / 1000) * (NOW - EPOCH)));
		$('#date_range').data('startDate',startDate);
		$('#date_range').data('endDate',endDate);
		$('#date_range_val').empty().append(startDate.toISOString() + ' - ' + endDate.toISOString());
		showit();
	    }
	});
    $('#main').append('<span id="date_range_val"></span>');
    $('#main').append('<div id="images"></div>').find('#images');
    $.getJSON('/mvco/api/autoclass/list_classes', function(r) {
	$.each(r, function(ix, class_label) {
	    $('#class_select').append('<option value="'+class_label+'">'+class_label+'</option>');
	});
	$('#class_select').change(showit);
    });
    $(window).scroll(loadImages);
});