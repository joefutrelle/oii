// allow the user to choose a percent.
// calls back every time the user moves the percent control, with the value
// requires knob.js
// this doesn't do much more than knob.js does, but handles range, basic styling, and focus
(function($) {
    $.fn.extend({
        percentPicker: function(callback) {
	    return this.each(function() {
		var $this = $(this);
		$this.append('<input class="percentKnob" type="text">')
		    .find('.percentKnob')
		    .attr('value',0)
		    .attr('data-min',0)
		    .attr('data-max',100)
		    .attr('data-width',100)
		    .attr('data-height',100)
		    .attr('data-thickness',1)
		    .attr('data-fgColor','#222222')
		    .attr('data-bgColor','gray')
		    .knob({'change': function(value) {
			$this.find('.percentKnob').css('color','white');
			if(callback != undefined) {
			    callback(value);
			}
		    }}).find('.percentKnob').focus(function(event) {
			// disallow focusing on text
			$(this).blur();
		    });
	    });
	}
    });
})(jQuery);

