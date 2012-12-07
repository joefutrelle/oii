function emptyExistingTable() {
    $('#existingTableContainer').empty();
	    $('#existingTableContainer').append('<table id="existingTable"  style="width:100%; cellpadding="0" ' + 
	    'cellspacing="0" border="1"></table>') ;

	$('#existingTable').append('<thead><tr class="ui-widget-header">'
				+ '<th>Class Name</th>'
				+ '<th>Username </th>'
				+ '<th>Timestamp</th></tr></thead>'
				+ '<tbody class="ui-widget-content"></tbody>'
				);	
}
 
function addExistingRow(ann){
	
	$('#existingTable tbody').append('<tr '
				+ 'id="' +ann.pid + '" class="ui-state-default" >'
				+ '<td >' + categoryLabelForPid(ann.category)  + '</td>'
				+ '<td>' + ann.annotator + '</td>'
				+ '<td>' + ann.timestamp + '</td></tr>'
				);		
	if (ann.deprecated){
		$('#existingTable').find('tr:last').addClass('strikethrough');
		
	}

}

function updateExistingTable(){
			$('#existingTable').dataTable({"sPaginationType": "full_numbers"});
			
			$("table#existingTable tbody").selectable({
				filter: 'tr',
				cancel: 'td.sort'
			}).sortable({
				delay: 100,
				axis: 'y',
				placeholder: 'ui-state-highlight',
				handle: 'td.sort',
				helper: function(e, ui) {
			ui.children().each(function() {
				$(this).width($(this).width());
			});
			
			/*********************/
			/* Do something here */
			/*********************/
			
			return ui;
		},
		start: function(event, ui) {
			ui.placeholder.html('<td colspan="99">&nbsp;</td>');
		},
		update: function(event, ui) {
			document.body.style.cursor = 'wait';
			//update stuff here                    

			// Ajax call to php file
			// On success
			document.body.style.cursor = 'default';
		},
		stop: function(event, ui) { /*  Reset and add odd and even classes     */
			$("tr:even").removeClass("odd even").addClass("even");
			$("tr:odd").removeClass("odd even").addClass("odd");
		}
	}).disableSelection();

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
