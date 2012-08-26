(function($) {
    $.fn.extend({
	timeline: function() {
            return this.each(function() {
                var $this = $(this);
		function screenToDate(event) {
		    var x = event.clientX - $this.find('div.timeline-frame div').offset().left;
		    return new Date(event.data.timeline.screenToTime(x))
		}
		$this.bind('showdata', {timeline:timeline}, function(event, data, options) {
		    if(options == undefined) {
			options = {
			    "width":  "100%",
			    "height": "200px",
			    "style": "box"
			}
		    }
		    console.log('trying to install timeline on '+$this.get(0));
		    timeline = new links.Timeline($this.get(0))
		    timeline.recalcConversion();
		    timeline.draw(data, options);
		    $this.bind('mousemove', {timeline:timeline}, function(event) {
			$this.trigger('dateHover', [screenToDate(event), event.clientX]);
		    });
		    $this.bind('click', {timeline:timeline}, function(event) {
			$this.trigger('dateClick', screenToDate(event));
		    });
		});
            });
        }//timeline
    });//$.fn.extend
})(jQuery);