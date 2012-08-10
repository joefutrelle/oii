
function emptyExistingLi() {
	   $('fieldset:contains("Existing Annotations") li').remove();
}

function addExistingLi(ann){
	$('fieldset:contains("Existing Annotations") ol').append(
			'<li class="ui-widget-content" id="' + ann.pid + '">' 
				 +'<div><b>Scope:</b> ' + ann.scope + '</div>'
				 +'<div><b>Category: </b>' + categoryLabelForPid(ann.category) + '</div>'
				 +'<div><b>Annotator:</b> ' + ann.annotator + '</div>'
				 //+'<div >' + ann.timestamp + '</div>'
				+'<div><b>Dep: </b>' + ann.deprecated + '</div>'
				+'<div><b>ID: </b>' + ann.pid + '</div>'
			+ '</li>' );

}

//the non-qaqc table is below

function emptyExistingTable() {
	    $('#existingTable').remove();
	    $('#rightPanel').append('<table id="existingTable"></table>')
      		  .find('div:last');

	$('#existingTable').append('<tr><th>Scope</th>'
				+ '<th>Class Name</th>'
				+ '<th>Annotator</th>'
				+ '<th>Timestamp</th></tr>'
				);
}

function addExistingRow(scope,category,annotator,timestamp){
	$('#existingTable').append('<tr><td>' + scope + '</td>'
				+ '<td>' + category + '</td>'
				+ '<td>' + annotator + '</td>'
				+ '<td>' + timestamp + '</td></tr>'
				);
}




/*
 var ann = {
		image: 'sdfa',
		category: 'scallop',
		//geometry: {},
		annotator: 'http://foobar/amber',
		scope: 'badfed',
		timestamp: '23432'iso8601(new Date()),
		//assignment: $('#workspace').data('assignment').pid
	    };

*/


