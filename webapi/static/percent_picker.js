// allow the user to choose a percent.
// calls back every time the user changes the percent value
(function($) {
    $.fn.extend({
        percentPicker: function(callback) {
	    return this.each(function() {
		var $this = $(this);
		function updateSliderValue() {
		    var val = $this.find('.percentSlider').slider('value');
		    $this.find('.percentValue').html(val+'%');
		    return val;
		}
		$this.append('<div><span class="percentSlider"></span><span class="percentValue"></span></div>')
		    .find('div').css('display','inline-block')
		    .find('.percentSlider:last')
		    .slider({
			orientation: 'horizontal',
			range: 'min',
			max: 100,
			value: 50,
			slide: updateSliderValue,
			change: function() {
			    var val = updateSliderValue();
			    callback(val);
			}
		    });
		updateSliderValue();
	    });
	}
    });
})(jQuery);

