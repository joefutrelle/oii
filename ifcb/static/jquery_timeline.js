(function($) {
    $.fn.extend({
	timeline: function() {
            return this.each(function() {
                var $this = $(this);
		var timeline = new links.Timeline($this.get(0))
		timeline.recalcConversion();
		// timeline is stored in the node data for access during event handling
		$this.data('timeline',timeline);
		// convert click to date FIXME remove see below
		function screenToDate(event) {
		    var x = event.clientX - $this.find('div.timeline-frame div').offset().left;
		    return new Date(event.data.timeline.screenToTime(x))
		}
		// FIXME remove these in deference to timeline's event API
		// and use timeline_bind in calling scripts
		$this.bind('mousemove', {timeline:timeline}, function(event) {
		    $.extend(timeline, { hoverDate: screenToDate(event) })
		    //$this.trigger('dateHover', [screenToDate(event), event.clientX]);
		});
		$this.bind('click', {timeline:timeline}, function(event) {
		    console.log('clicked on '+screenToDate(event));
		    $.extend(timeline, { clickDate: screenToDate(event) })
		    //console.log('extending timeline with clickDate');
		    //$this.trigger('dateClick', [screenToDate(event), event.clientX]);
		});
		// trigger this when you want to show data
		// FIXME should deal with being triggered twice in a row
		$this.bind('showdata', function(event, data, options) {
		    if(options == undefined) {
			options = {
			    "width":  "100%",
			    "height": "200px",
			    "style": "box"
			}
		    }
		    timeline.draw(data, options);
		});
            });
        },//timeline
	getTimeline: function(callback) {
	    // provide direct access to the timeline object in a callback
	    return this.each(function() {
		var $this = $(this);
		// find the
		var timeline = $this.data('timeline');
		if(timeline != undefined) {
		    callback(timeline)
		}
	    });
	},//getTimeline
	timeline_bind: function(event, callback) {
	    // here we allow binding to timeline's events, and in the handler
	    // pass the timeline object back, so the timeline API can be used,
	    // followed by whatever arguments the timeline event callback expects
	    // see http://almende.github.com/chap-links-library/js/timeline/doc/#Events
	    return this.each(function() {
		var $this = $(this);
		// find the
		var timeline = $this.data('timeline');
		if(timeline == undefined) {
		    console.log('no timeline!');
		    return;
		}
		// use links event API to attach an internal wrapper callback
		links.events.addListener(timeline, event, function() {
		    // in which we prepend timeline to the arguments and call the external callback
		    // convert arguments to array per http://www.mennovanslooten.nl/blog/post/59
		    var args = [].splice.call(arguments,0);
		    callback.apply(this, [timeline].concat(args)); // call the external callback
		});
	    });
	}//timeline_bind
    });//$.fn.extend
})(jQuery);