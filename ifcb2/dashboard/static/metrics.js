(function($) {
    $.fn.extend({
	metric: function(data, key, label) {
            return this.each(function() {
                var $this = $(this);
		var series = [];
		var minDate = Date.parse(data[0].date);
		var maxDate = minDate;
		$.each(data,function(ix,dm) {
		    var d = Date.parse(dm.date);
		    if(d > maxDate) {
			maxDate = d;
		    }
		    series.push([d, dm[key]]);
		});
		$.plot($this,[series],{
		    colors: [ '#ff0000' ],
		    xaxis: {
			mode: 'time',
			timeformat: '%y-%m-%d %H:%M',
			min: minDate,
			max: maxDate
		    },
		    lines: {
			show: true,
			steps: true
		    }
		});
	    });
	}
    });//$.fn.extend
})(jQuery);
