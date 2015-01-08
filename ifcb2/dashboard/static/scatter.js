function scatter_setup(elt, timeseries, pid, width, height) {
    var ENDPOINT_PFX = 'data_scat_ep_pfx';
    var ENDPOINT_SFX = 'data_scat_ep_sfx';
    var WIDTH = 'data_scat_ep_width';
    var HEIGHT = 'data_scat_ep_height';
    var PLOT_OPTIONS = 'data_scat_options';
    $(elt).data(ENDPOINT_PFX, '/'+timeseries+'/api/plot/');
    $(elt).data(ENDPOINT_SFX, '/pid/');
    $(elt).data(WIDTH, width);
    $(elt).data(HEIGHT, height);
    $(elt).data(PLOT_OPTIONS, {
	series: {
	    points: {
		show: true,
		radius: 2,
	    }
	},
	grid: {
	    clickable: true,
	    hoverable: true,
	    autoHighlight: true
	},
	selection: {
	    mode: "xy",
	    color: "red"
	}
    });
    $(elt).siblings('.bin_view_controls')
	.find('.bin_view_specific_controls')
	.empty()
	.append('{plot controls}');
    $(elt).unbind('show_bin').bind('show_bin',function(event, bin_pid) {
	var endpoint = $(elt).data(ENDPOINT_PFX) + 'x/left/y/bottom' + $(elt).data(ENDPOINT_SFX) + bin_pid;
	var plot_options = $(elt).data(PLOT_OPTIONS);
	console.log("Loading "+endpoint+"...");
	$.getJSON(endpoint, function(r) {
	    console.log("Got JSON data");
	    var bin_pid = r.bin_pid;
	    var roi_pids = [];
	    var point_data = [];
	    $.each(r.points, function(ix, point) {
		point_data.push([point.x, point.y]);
		roi_pids.push(bin_pid + '_' + point.roi_num);
	    });
	    var plot_data = {
		label: 'hello',
		data: point_data,
		color: "black",
		points: {
		    fillColor: "black"
		},
		highlightColor: "red"
	    };
	    $(elt).empty()
		    .css('width',$(elt).data(WIDTH))
		    .css('height',$(elt).data(HEIGHT))
		    .plot([plot_data], plot_options);
	    $(elt).data('roi_pids', roi_pids);
	    $(elt).data('point_data', point_data);
	});
	$(elt).bind("plotselected", function(evt, ranges) {
	    console.log(evt);
	    $(evt.target).addClass("plotselected");//not sure what this does
	    // receive selection range from event
	    lo_x = ranges.xaxis.from;
	    hi_x = ranges.xaxis.to;
	    lo_y = ranges.yaxis.from;
	    hi_y = ranges.yaxis.to;
	    // replace the roi image view with this mosaic view
	    $('#roi_image').empty()
		.closeBox()
		.css('display','inline-block')
		.css('width','45%');
	    // for each point on the scatter plot,
	    $.each($(elt).data('point_data'), function(ix, point) {
		var x = point[0];
		var y = point[1];
		// if it's in the selection rectangle
		if(x >= lo_x && x <= hi_x && y >= lo_y && y <= hi_y) {
		    // draw the roi
		    var pid = $(elt).data('roi_pids')[ix];
		    $('#roi_image').append('<a href="'+pid+'.html"><img src="'+pid+'.jpg"></img></a>');
		}
	    });
	});
	$(elt).bind("plotclick", function(evt, pos, item) {
	    console.log(evt);
	    if($(evt.target).hasClass("plotselected")) {
		$(evt.target).removeClass("plotselected");
		return;
	    } else if(item) {
		var roi_pids = $(elt).data('roi_pids');
		if(!roi_pids) { return };
		roi_pid = roi_pids[item.dataIndex];
		// fire a roi clicked event
		$(elt).trigger('roi_click',roi_pid);
	    }
	})
    });
}
//jquery plugin
(function($) {
    $.fn.extend({
	scatter: function(timeseries, pid, width, height) {
	    return this.each(function() {
		var $this = $(this);
		$this.css('width',width)
		    .css('height',height);
		scatter_setup($this, timeseries, pid, width, height);
		console.log('triggering show_bin for scatter');
		$this.trigger('show_bin',[pid]);
	    });//each
	}//scatter
    });//$.fn.extend
})(jQuery);//end of plugin
