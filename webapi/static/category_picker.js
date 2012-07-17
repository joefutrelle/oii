// mmm mm some tasty jQuery extensibility
(function($) {
    $.fn.extend({
        categoryPicker: function(mode, scope, callback) {
	    return this.each(function() {
		var $this = $(this);
		$this.data('all_categories',[]); // stores the result of /list_categories call
		$this.data('recent',[]);
		// a user has changed a selection; compute the selected multi-class and callback
		function compute_selected() {
		    var selectedCategories = [];
		    var label = '';
		    // for each SELECT node, figure out which category is selected
		    $this.find('select').each(function(ix, elt) {
			var pid = $(elt).val();
			$.each($this.data('all_categories'), function(ix, c) {
			    if(c.pid == pid) {
				// push this on our list of selected categories
				selectedCategories.push(c);
				label += ' + ' + c.label; // and our text label
			    }
			});
		    });
		    // we have the list of selected categories; call the callback
		    callback(selectedCategories, scope);
		}
		// add a new class selector and its associated "-" button for if/when the user wants to remove it
		function add_choice() {
		    // add all categories to the select
		    var select = $this.append('<div><select class="category_choice"></select></div>').find('select');
		    $(select).append('<option value="NONE">(None)</option>');
		    $.each($this.data('all_categories'),function(ix,c) {
			$(select).append('<option value="'+c.pid+'">'+c.label+'</option>')
		    });
		    // now make all buttons "-" buttons (including the last one, which will be a "+" button at this point)
		    $this.find('.button').replaceWith('<a href="#" class="button">-</a>').end()
			.find('.button').button().click(function() {
			    // a "-" button removes the selector, and recomputes the selected category accordingly
			    $(this).parent().remove();
			    compute_selected();
			});
		    // now add the "+" button to the last selector. its click handler is add_choice
		    $this.find('div:last').append('<a href="#" class="button">+</a>').find('.button').button().click(add_choice);
		    // the change handler for the select is compute_selected
		    $(select).change(compute_selected);
		}
		// now actually do something: call list_categories, save the result, and add the first selector
		$.getJSON('/list_categories/'+mode+'/'+scope, function(c) {
		    $this.data('all_categories',c);
		    $this.append('<div class="selected_category"></div>');
		    add_choice();
		});
	    });
	}
    });
})(jQuery);
$(document).ready(function() {
    $('#picker1').categoryPicker('QC_Fish',function(categories) {
    });
    $('#picker2').categoryPicker('QC_Fish',function(categories) {
    });
});

