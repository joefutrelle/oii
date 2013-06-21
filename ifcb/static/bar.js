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
	    $(elt).find('a').append('<img src="'+img_src+'">');
	    $(elt).removeClass('roi_image_unloaded').addClass('roi_image');
	}
    });
}
function showit() {
    var class_label = $('#class_select').val();
    var threshold = $('#threshold').slider('value') / 100.0;
    //$.getJSON('/mvco/api/autoclass/rois_of_class/'+class_label+'/threshold/'+threshold+'/start/2012-07-04/end/2012-07-05', function(r) {
    $('#images').empty().append('please wait...');
    $.getJSON('/mvco/api/autoclass/rois_of_class/'+class_label+'/threshold/'+threshold, function(r) {
	$('#images').empty();
	$.each(r, function(ix, roi_pid) {
	    if(ix < 100) {
		$('#images').append('<div><a href="'+roi_pid+'.html"></a>'+roi_pid+'</div>')
		    .find('div:last')
		    .addClass('roi_image_unloaded')
		    .data('img_src',roi_pid+'.png');
	    }
	});
	loadImages();
    });
}
$(document).ready(function() {
    $('#main').append('<select id="class_select"></select>').find('#class_select');
    $('#main').append('<div style="display: inline-block; width: 300px" id="threshold">').find('#threshold')
	.slider({
	    min: 1,
	    max: 99,
	    value: 99,
	    change: function () {
		$('#threshval').empty().append('' + $('#threshold').slider('value') / 100.0);
		showit();
	    }
	});
    $('#main').append('<span id="threshval"></span>');
    $('#main').append('<div id="images"></div>').find('#images');
    $.getJSON('/mvco/api/autoclass/list_classes', function(r) {
	$.each(r, function(ix, class_label) {
	    $('#class_select').append('<option value="'+class_label+'">'+class_label+'</option>');
	});
	$('#class_select').change(showit);
    });
    $(window).scroll(loadImages);
});