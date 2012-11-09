$(document).ready(function() {
	$('#quickinfo').append(
	'<fieldset><legend>Imagename</legend><span style="font-size:0.87em" id="quickImagename"></span></fieldset>'
		+ '<fieldset  "><legend>Assgnment Description</legend><span id="quickAssignment"></span></fieldset>'
		+ '<fieldset style="width:40% ; float:left;"><legend>Assignment Position</legend>'
		+ '<span id="quickOffset"></span>'
		+ '<span id="quickNumImages"></span></fieldset>'
		+ '<fieldset style="width:20%; float:left;"><legend>Progress</legend><span id="quickProgress"></span></fieldset>'
		 
	)

});

//addition for displaying info
//	$('#quickOffset').val(offset);

