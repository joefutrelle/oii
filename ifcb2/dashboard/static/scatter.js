function scatter_setup(elt, timeseries, pid, width, height) {
    var $this = $(elt);
    var ENDPOINT_PFX = 'data_scat_ep_pfx';
    var ENDPOINT_SFX = 'data_scat_ep_sfx';
    var WIDTH = 'data_scat_ep_width';
    var HEIGHT = 'data_scat_ep_height';
    var PLOT_OPTIONS = 'data_scat_options';
    var PLOT_TYPE = 'data_scat_plot_type';
    var PLOT_X = 'data_scat_x_axis';
    var PLOT_Y = 'data_scat_y_axis';
    var endpointPfx = '/'+timeseries+'/api/plot';
    var endpointSfx = '/pid/';
    $this.data(HEIGHT, height);
    var plotTypes = ['linear','log'];
    var plotType = $this.data(PLOT_TYPE);
    if(plotType==undefined) {
	plotType=plotTypes[0];
    }
    var plotXs = ['bottom','fluorescenceLow'];
    var plotX = $this.data(PLOT_X);
    if(plotX==undefined) {
	plotX = plotXs[0];
    }
    var plotYs = ['left','scatteringLow'];
    var plotY = $this.data(PLOT_Y);
    if(plotY==undefined) {
	plotY = plotYs[0];
    }
    var plotOptions = {
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
    };
    if(plotType=='log') {
	var xf = {
	    transform: function(v) {
		return v == 0 ? v : Math.log(v);
	    },
	    inverseTransform: function(v) {
		return Math.exp(v);
	    }
	};
	plotOptions.xaxis = xf;
	plotOptions.yaxis = xf;
    }
    $this.data(PLOT_OPTIONS, plotOptions);
    $this.siblings('.bin_view_controls')
	.find('.bin_view_specific_controls')
	.empty()
	.append('<br>Type: <span></span>') // plot type: linear / log
	.find('span:last')
	.radio(plotTypes, function(plotType) {
	    return plotType;
	}, plotType).bind('select', function(event, value) {
	    $this.data(PLOT_TYPE, value);
	    $this.trigger('drawBinDisplay');
	});
    $this.siblings('.bin_view_controls')
	.find('.bin_view_specific_controls')
	.append('X axis: <span></span>') // x axis
	.find('span:last')
	.radio(plotXs, function(plotX) {
	    return plotX;
	}, plotX).bind('select', function(event, value) {
	    $this.data(PLOT_X, value);
	    $this.trigger('drawBinDisplay');
	})
    $this.siblings('.bin_view_controls')
	.find('.bin_view_specific_controls')
	.append('Y axis: <span></span>') // y axis
	.find('span:last')
	.radio(plotYs, function(plotY) {
	    return plotY;
	}, plotY).bind('select', function(event, value) {
	    $this.data(PLOT_Y, value);
	    $this.trigger('drawBinDisplay');
	});
    $this.unbind('show_bin').bind('show_bin',function(event, bin_pid) {
	var plotParams = params2url({
	    'x': plotX,
	    'y': plotY
	});
	var endpoint = endpointPfx + plotParams + endpointSfx + bin_pid;
	var plot_options = $this.data(PLOT_OPTIONS);
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
		label: 'hello', // FIXME derive from axes
		data: point_data,
		color: "black",
		points: {
		    fillColor: "black"
		},
		highlightColor: "red"
	    };
	    $this.empty()
		    .css('width',$this.data(WIDTH))
		    .css('height',$this.data(HEIGHT))
		    .plot([plot_data], plot_options);
	    $this.data('roi_pids', roi_pids);
	    $this.data('point_data', point_data);
	});
	$this.bind("plotselected", function(evt, ranges) {
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
	    $.each($this.data('point_data'), function(ix, point) {
		var x = point[0];
		var y = point[1];
		// if it's in the selection rectangle
		if(x >= lo_x && x <= hi_x && y >= lo_y && y <= hi_y) {
		    // draw the roi
		    var pid = $this.data('roi_pids')[ix];
		    $('#roi_image').append('<a href="'+pid+'.html"><img src="'+pid+'.jpg"></img></a>');
		}
	    });
	});
	$this.bind("plotclick", function(evt, pos, item) {
	    console.log(evt);
	    if($(evt.target).hasClass("plotselected")) {
		$(evt.target).removeClass("plotselected");
		return;
	    } else if(item) {
		var roi_pids = $this.data('roi_pids');
		if(!roi_pids) { return };
		roi_pid = roi_pids[item.dataIndex];
		// fire a roi clicked event
		$this.trigger('roi_click',roi_pid);
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
