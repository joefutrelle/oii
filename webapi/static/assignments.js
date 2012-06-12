function toggleAssignments(){

	if ($("#assignments").length > 0){
		 $('#assignments').remove();
	  
	} else {
	 createAssignmentsPanel();
	}
	
}

function createAssignmentsPanel() {
	$('#controls').append('<div id="assignments"></div>')
	$('#assignments').append('<fieldset id="assignmentOptions">OPTIONS: sorting, filtering etc</fieldset>')
	    $.getJSON('/list_assignments', function(r) {
		$.each(r.assignments, function(i,a) {
		    clog(a);
		$('#assignments').append('<div class="assignmentBox">'
			+'<h2><span>Assignment:</span> ' + a.pid +'</h2>'
			
			+'<div><ul>'
			+'<li><span>Project:</span> ' + a.project_name+'</li>'
			+'<li><span>IDmode:</span> ' + a.idmode+'</li>'
			+'<li><span>Priority:</span> ' + a.priority+'</li>'
			+'<li><span>Description:</span> ' + a.description+'</li>'
			+'<li><span>date created:</span> ' + a.date+'</li>'
			+'<li><span>created by:</span> ' + a.initials+'</li>'
			+'</ul></div>'
			+'<div>Log entries from this assignment</div>'
			+'<div style="float:right">'
				+'<a href="#" id="addAssignmentComment" class="button">add Note</a></br>'
				+'<a href="#" id="startAssignment" class="button">Start/Continue</a>'
			+'</div>'
			+'<br style="clear:both;"/>'
			+ '</div>' /*assignments*/
		)

		});
	    });
}

$(document).ready(function() {
	createAssignmentsPanel();
	$('#viewAssignments').click(function() {
		toggleAssignments();
	});


});

