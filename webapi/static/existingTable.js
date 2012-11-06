function emptyExistingTable() {
    $('#existingTableContainer').empty();
	    $('#existingTableContainer').append('<table id="existingTable" class="dataTable"  cellpadding="0" ' + 
	    'cellspacing="0" border="0"></table>') ;

	$('#existingTable').append('<thead><tr>'
				+ '<th>Class Name</th>'
				+ '<th>Annotator</th>'
				+ '<th>Timestamp</th></tr></thead><tbody></tbody>'
				);
	
}

function addExistingRow(ann){
	$('#existingTable tbody').append('<tr>'
				+ '<td>' + categoryLabelForPid(ann.category)  + '</td>'
				+ '<td>' + ann.annotator + '</td>'
				+ '<td>' + ann.timestamp + '</td></tr>'
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


