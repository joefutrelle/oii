// mmm mm some tasty jQuery extensibility
(function($) {
    $.fn.extend({
        categoryPicker: function(mode, scope, callback, showPercentCover,showAdd) {
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
			var percentCover = $(elt).data('percentCover');
			$.each($this.data('all_categories'), function(ix, c) {
			    if(c.pid == pid) {
				if(percentCover != undefined) {
				    c.percent_cover = percentCover;
				}
				// push this on our list of selected categories
				selectedCategories.push(c);
				label += ' + ' + c.label; // and our text label
			    }
			});
		    });
		    // we have the list of selected categories; call the callback
		    callback(selectedCategories, scope);
		    $this.find('.selected_category').html(label.substring(2));
		}
		// add a new class selector and its associated "-" button for if/when the user wants to remove it
		function add_choice() {
		    // add all categories to the select
		    var select = $this.append('<div><select class="category_choice"></select></div>').find('select:last');
		    $(select).append('<option value="NONE">(None)</option>');
		    $.each($this.data('all_categories'),function(ix,c) {
			$(select).append('<option value="'+c.pid+'">'+c.label+'</option>')
		    });
		    // now make all buttons "-" buttons (including the last one, which will be a "+" button at this point)
		    if(showAdd){
		    $this.find('.button').replaceWith('<a href="#" class="button">-</a>').end()
			.find('.button').button().click(function() {
			    // a "-" button removes the selector, and recomputes the selected category accordingly
			    $(this).parent().remove();
			    compute_selected();
			});
		    // now add the "+" button to the last selector. its click handler is add_choice
		    $this.find('div:last').append('<a href="#" class="button">+</a>').find('.button').button().click(add_choice);
			}
		    //
		    if(showPercentCover) {
			$this.find('div:last').percentPicker(function(pct) {
			    // stash the value on the select element
			    $(select).data('percentCover',pct);
			    compute_selected();
			});
		    }
		    // the change handler for the select is compute_selected
		    $(select).change(compute_selected);
		}
		function resetPicker() { 
			$this.find('.resetButton').button().click(reset);
			}
		function reset() {
		    $.getJSON('/list_categories/'+mode+'/'+scope, function(c) {
			$this.data('all_categories',c);
			$this.empty();
			$this.append('<div class="selected_category"></div>');
			$this.append('<a href="#" class="resetButton hidden">reset</a>');
			resetPicker();
			add_choice();
		    });
		}		
		// now actually do something: call list_categories, save the result, and add the first selector
		reset();
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

