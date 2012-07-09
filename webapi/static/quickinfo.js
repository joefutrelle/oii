$(document).ready(function() {
	$('#quickinfo').append('<div><b>Imagename:</b><span id="quickImagename"></span></div>'
		+ '<div><b>Assignment Position:</b><span id="quickOffset"></span>/<span id="quickNumImages"></span></div>'

	)
	$("#quickImagename").html("?");
	$("#quickOffset").html("?");
	$("#quickNumImages").html("?");


});

//addition for displaying info
//	$('#quickOffset').val(offset);

