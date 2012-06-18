// mmm mm some tasty jQuery extensibility
(function($) {
    $.fn.extend({
        categoryPicker: function(mode, scope, callback) {
	    return this.each(function() {
		var $this = $(this);
		$this.data('all_categories',[]);
		$this.data('recent',[]);
		function compute_selected() {
		    var selectedCategories = [];
		    var label = '';
		    $this.find('select').each(function(ix, elt) {
			var pid = $(elt).val();
			$.each($this.data('all_categories'), function(ix, c) {
			    if(c.pid == pid) {
				selectedCategories.push(c);
				label += ' + ' + c.label;
			    }
			});
		    });
		    $this.find('.selected_category')
			.html('<a href="#">'+label.substring(2)+'</a>')
			.find('a').button()
			.click(function() {
			    callback(selectedCategories);
			});
		}
		function add_choice() {
		    var select = $this.append('<div><select class="category_choice"></select></div>').find('select');
		    $.each($this.data('all_categories'),function(ix,c) {
			$(select).append('<option value="'+c.pid+'">'+c.label+'</option>')
		    });
		    $this.find('.button').replaceWith('<a href="#" class="button">-</a>').end().find('.button').button().click(function() { $(this).parent().remove(); compute_selected(); });
		    $this.find('div:last').append('<a href="#" class="button">+</a>').find('.button').button().click(add_choice);
		    $(select).change(compute_selected);
		}
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

