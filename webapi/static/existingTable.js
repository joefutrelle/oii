

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


