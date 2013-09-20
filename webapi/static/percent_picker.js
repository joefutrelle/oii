// allow the user to choose a percent.
// calls back every time the user changes the percent value
(function($) {
    $.fn.extend({
        percentPicker: function(callback) {
	    return this.each(function() {
		var $this = $(this);
		function updateSliderValue() {
		   // var valMAP = [0,10,25,50,75,90,100];
		    var val = $this.find('.percentSlider').slider('value');
			//val = valMAP[val];
		    $this.find('.percentValue').html(val+'%');
		    callback(val);
		}
		$this.append('<div><span class="percentSlider"></span><span class="percentValue"></span></div>')
		    .find('div').css('display','inline-block')
		    .find('.percentSlider:last')
		    .slider({
			orientation: 'horizontal',
			range: 'min',
			max: 100,
			value: 0,
			step: 10,
			slide: updateSliderValue,
			change: function() {
			    updateSliderValue();
			}
		    });
		updateSliderValue();
	    });
	}
    });
})(jQuery);

