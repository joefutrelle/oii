// jQuery UI plugin providing grouped radio button
// selection of arbitrary values
// params:
// choices - either a list in the form [[label1, value1], [label2, value2], ... [labeln, valuen]]
// or a list of values to be serialized using the specified function
// tostring - a function that converts values to labels
// events:
// select(value) - a value is selected
(function($) {
    $.fn.extend({
	// each choice is a sequence of label, value
	radio: function(choices, tostring) {
	    if(tostring != undefined) {
		var newChoices = [];
		$.each(choices, function(ix, choice) {
		    newChoices.push([tostring(choice), choice]);
		});
		choices = newChoices;
	    }
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		$this.empty();
		$.each(choices, function(ix, choice) {
		    var label = choice[0];
		    var value = choice[1];
		    $this.append('<a>'+label+'</a>')
			.find('a:last')
			.button()
			.click(function() {
			    $this.trigger('select', [value]);
			});//click
		});//each choice
	    });// each in radio
	}//radio
    });//$.fn.extend
})(jQuery);//end of plugin
