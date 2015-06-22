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
		// support for animating to new time
		// based on http://almende.github.com/chap-links-library/js/timeline/examples/example21_animate_visible_range.html
		// create a simple animation
		var animateTimeout = undefined;
		var animateFinal = undefined;
		function animateTo(date) {
		    // get the new final date
		    animateFinal = date.valueOf();
		    
		    // cancel any running animation
		    if (animateTimeout) {
			clearTimeout(animateTimeout);
			animateTimeout = undefined;
		    }
		    // animate towards the final date
		    function animate() {
			var range = timeline.getVisibleChartRange();
			var current = (range.start.getTime() + range.end.getTime())/ 2;
			var width = (range.end.getTime() - range.start.getTime());
			var minDiff = Math.max(width / 1000, 1);
			var diff = (animateFinal - current);
			if (Math.abs(diff) > minDiff) {
			    // move towards the final date
			    var start = new Date(range.start.getTime() + diff / 3);
			    var end = new Date(range.end.getTime() + diff / 3);
			    timeline.setVisibleChartRange(start, end);
			    timeline.trigger('rangechange');

			    // start next timer
			    animateTimeout = setTimeout(animate, 20);
			} else {
			    timeline.trigger('rangechanged');
			}
		    };
		    animate();
		}
		// FIXME remove these in deference to timeline's event API
		// and use timeline_bind in calling scripts
		$this.bind('mousemove', {timeline:timeline}, function(event) {
		    $.extend(timeline, { hoverDate: screenToDate(event) })
		    //$this.trigger('dateHover', [screenToDate(event), event.clientX]);
		});
		$this.bind('click', {timeline:timeline}, function(event) {
		    var inControls = 0;
		    if($(event.target).hasClass('timeline-navigation-zoom-in') ||
		       $(event.target).hasClass('timeline-navigation-zoom-out')) {
			animateTo(timeline.getCustomTime());
		    }
		    if($(event.target).hasClass('timeline-navigation-zoom-in') ||
		       $(event.target).hasClass('timeline-navigation-zoom-out') ||
		       $(event.target).hasClass('timeline-navigation-move-left') ||
		       $(event.target).hasClass('timeline-navigation-move-right')) {
			event.stopImmediatePropagation(); // user clicked on the controls
		    }
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
		    // if utc is set, then make sure current time and custom time are offset by UTC
		    if(options.utc) {
			var now = new Date();
			var nowOffset = new Date(now.getTime() + (now.getTimezoneOffset() * 60000));
			timeline.setCurrentTime(nowOffset);
			if(options.showCustomTime) {
			    timeline.setCustomTime(nowOffset);
			}
		    }
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
