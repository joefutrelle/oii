(function($) {
    $.fn.extend({
       timeline: function() {
            return this.each(function() {
                var $this = $(this);
		var timeline;
		console.log('loading data series...');
		$.getJSON('/api/volume', function(volume) {
		    // Create and populate a data table.
		    var data = [];
		    $.each(volume, function(ix, day_volume) {
			var bin_count = day_volume.bin_count;
			var date = day_volume.day; // should be 'date'
			var gb = day_volume.gb;
			var year = date.split('-')[0];
			var month = date.split('-')[1];
			var day = date.split('-')[2];
			var start = new Date(year, month-1, day)
			var end = new Date(year, month-1, day);
			end.setHours(end.getHours() + 24);

			// create item with actual number
			var height = Math.round(gb * 15);
			var style = 'height:' + height + 'px;'
			var color = '#ff0000';
			style = 'height:' + height + 'px;' +
			    'background-color: ' + color + ';'+
			    'border: 1px solid ' + color + ';';
			var actual = '<div class="bar" style="' + style + '" ' +
			    ' title="'+gb+'GB"></div>';
			var item = {
			    'group': 'Data volume',
			    'start': start,
			    'end': end,
			    'content': actual
			};
			data.push(item);
		    });

		    // specify options
		    var options = {
			"width":  "100%",
			"height": "200px",
			"style": "box"
		    };

		    // Instantiate our timeline object.
		    console.log('trying to install timeline on '+$this.get(0));
		    timeline = new links.Timeline($this.get(0))
		    timeline.recalcConversion();
		    function screenToDate(event) {
			var x = event.clientX - $this.find('div.timeline-frame div').offset().left;
			return new Date(event.data.timeline.screenToTime(x))
		    }
		    $this.bind('mousemove', {timeline:timeline}, function(event) {
			$this.trigger('dateHover', screenToDate(event));
		    });
		    $this.bind('click', {timeline:timeline}, function(event) {
			$this.trigger('dateClick', screenToDate(event));
		    });

		    // Draw our timeline with the created data and options
		    timeline.draw(data, options);
		});
            });
        }//timeline
    });//$.fn.extend
})(jQuery);