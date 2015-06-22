// jQuery UI plugin providing grouped radio button
// selection of arbitrary values
// params:
// choices - either a list in the form [[label1, value1], [label2, value2], ... [labeln, valuen]]
// or a list of values to be serialized using the specified function
// tostring - a function that converts values to labels
// events:
// select(value) - a value is selected
(function($) {
    var seq = 0;
    $.fn.extend({
	// each choice is a sequence of label, value
	// or its a list of values and tostring is a function that returns a label for each one
	// selected (optional) is the one that should initially be selected
	radio: function(choices, tostring, selected) {
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
		var name='jquery_radio_'+(seq++);
		$.each(choices, function(ix, choice) {
		    var label = choice[0];
		    var value = choice[1];
		    var isSelected = JSON.stringify(value) == JSON.stringify(selected);
		    var checked = isSelected ? ' checked="checked"' : '';
		    var id='jquery_radio_'+(seq++);
		    $this.append('<input type="radio" name="'+name+'" id="'+id+'"'+checked+'><label for="'+id+'">'+label+'</label>')
			.find('input:last')
			.click(function() {
			    $this.trigger('select', [value]);
			});//click
		});//each choice
		setTimeout(function() {
		    $this.buttonset();
		}, 0);
	    });// each in radio
	}//radio
    });//$.fn.extend
})(jQuery);//end of plugin
