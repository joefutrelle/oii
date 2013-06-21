function showit() {
    var class_label = $('#class_select').val();
    var threshold = $('#threshold').slider('value') / 100.0;
    //$.getJSON('/mvco/api/autoclass/rois_of_class/'+class_label+'/threshold/'+threshold+'/start/2012-07-04/end/2012-07-05', function(r) {
    $('#images').empty().append('please wait...');
    $.getJSON('/mvco/api/autoclass/rois_of_class/'+class_label+'/threshold/'+threshold, function(r) {
	$('#images').empty();
	$.each(r, function(ix, roi_pid) {
	    if(ix < 100) {
		$('#images').append('<a href="'+roi_pid+'.html"><img src="'+roi_pid+'.png"></a>');
	    }
	});
    });
}
$(document).ready(function() {
    $('#main').append('<select id="class_select"></select>').find('#class_select');
    $('#main').append('<div style="display: inline-block; width: 300px" id="threshold">').find('#threshold')
	.slider({
	    min: 1,
	    max: 99,
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
});