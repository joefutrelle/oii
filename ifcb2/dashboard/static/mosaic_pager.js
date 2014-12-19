// jQuery plugin extending image_pager for IFCB mosaic images.
// obv requires image_pager.
// fires the following events
// page_change(pageNumber, page_url) - when the user changes the page; generally not used
// roi_click(roi_pid, width, height) - when the user clicks a ROI
// resizable version triggers
// state_change({pageNumber, width, height, roi_scale}) when state changes
// goto_bin(pid) - when the user clicks on the "next/prev" bin button
(function($) {
    $.fn.extend({
	mosaicPager: function(timeseries, pid, width, height, roi_scale) {
	    var BIN_URL='mosaic_bin_url';
	    // pid - bin pid (or lid)
	    // width -  the width  \__of the mosaic
	    // height - the height / 
	    // roi_scale - scale factor for ROIs
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		// put 30 pages on the pager, just in case it's a huge bin
		// FIXME somehow figure out how many pages there are re #1701
		var images = [];
		for(var page=1; page <= 30; page++) {
		    // each page is a mosaic API call URL with a successive page number
		    var url = '/'+timeseries+'/api/mosaic/size/'+width+'x'+height+'/scale/'+roi_scale+'/page/'+page+'/pid/'+pid+'.jpg';
		    images.push(url);
		}
		$.getJSON(pid+'_medium.json', function(r) {
		    $this.find('.imagepager_rois_total').empty().append(r.targets.length+'');
		    $this.find('.imagepager_date').attr('title',r.date).timeago();
		});
		// list of images in hand, create the image pager
		$this.empty().append('<div class="mosaic_pager_image_pager"></div>')
		    .append('<div class="imagepager_paging">page <span class="imagepager_page_number"></span>, showing <span class="imagepager_rois_shown">?</span> of <span class="imagepager_rois_total">?</span> target(s)</div>')
		/*
*/
		    .find('div.mosaic_pager_image_pager').imagePager(images, width, height) // use the image pager plugin
		    .bind('change', function(event, ix, image_href) { // when the user changes which page they're viewing
			$this.data(BIN_URL, image_href);
			$this.find('.imagepager_page_number').empty().append((ix+1)+'');
			$this.find('.imagepager_rois_shown').empty().append('&#x21BB;');
			$this.trigger('page_change', [ix+1, image_href]);
			$.getJSON(image_href.replace('.jpg','.json'), function(r) {
			    $this.find('.imagepager_rois_shown').empty().append(r.length+'');
			});
		    }).delegate('.page_image', 'click', function(event) { // when the user clicks on the mosaic image
			// figure out where the click was
			var clickX = event.pageX - $(this).offset().left;
			var clickY = event.pageY - $(this).offset().top;
			// now figure out which ROI the click was in. that requires the layout, see below
			function roi_click(layout) {
			    $.each(layout, function(ix, tile) {
				if(clickX >= tile.x && clickX <= tile.x + tile.width &&
				   clickY >= tile.y && clickY <= tile.y + tile.height) {
				    console.log('user clicked on '+tile.pid);
				    setTimeout(function() {
					$this.trigger('roi_click', tile.pid);
				    }, 0);
				}
			    });
			}
			// fetch it from the mosaic page image URL except with the extension "json"
			var mosaic_image_href = $this.data(BIN_URL);
			$.getJSON(mosaic_image_href.replace('jpg','json'), function(layout) {
			    roi_click(layout); // now figure out where the user clicked
			});
		    });
	    });//each in mosaicPager
	},//mosaicPager
        resizableBinView: function(timeseries, width, height, roi_scale, pid) {
	    var PID = 'bin_view_pid';
	    var WIDTH = 'bin_view_width';
	    var HEIGHT = 'bin_view_height';
	    var VIEW_TYPE = 'bin_view_view_type'
	    var ROI_SCALE = 'bin_view_roi_scale';
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		// store user preferences in data
		$this.data(PID, pid);
		$this.data(VIEW_TYPE, undefined ? 'mosaic' : $this.data(VIEW_TYPE));
		$this.data(WIDTH, width == undefined ? 800 : width);
		$this.data(HEIGHT, height == undefined ? 600 : height);
		$this.data(ROI_SCALE, roi_scale == undefined ? 0.33 : roi_scale);
		// add some controls for changing the size of the view
		var view_sizes = [[640, 480], [800, 600], [1280, 720], [1280, 1280]];
		var roi_scales = [15, 25, 33, 40, 66, 100];
		// make the selected one checked
		var selected_view = 'mosaic';
		var selected_size = undefined;
		function pageChanged(pageNumber) {
		    pageNumber == pageNumber ? pageNumber : 1;
		    $this.trigger('state_change', [{
			pageNumber: pageNumber,
			width: $this.data(WIDTH),
			height: $this.data(HEIGHT),
			roi_scale: $this.data(ROI_SCALE)}]);
		}
		$.each(view_sizes, function(ix, size) {
		    if(size[0] == $this.data(WIDTH) && size[1] == $this.data(HEIGHT)) {
			selected_size = size;
		    }
		});
		$this.append('<div class="bin_view_next_prev"></div>')
		$this.find('.bin_view_next_prev')
		    .append('<span class="controlGray biggerText previousBin">&#x25C0; Previous</span>')
		    .append('<span class="controlGray biggerText"> | </span>')
		    .append('<span class="controlGray biggerText nextBin">Next &#x25B6;</span>');
		// add size controls
		$this.append('<div class="bin_view_controls"></div>')
		    .find('.bin_view_controls')
		    .append('View: <span></span>')
		    .find('span:last')
		    .radio(['mosaic','plot'], function(viewType) {
			return viewType;
		    }, selected_view).bind('select', function(event, value) {
			console.log('view type =' + value);
		    });
		$this.find('.bin_view_controls')
		    .append('View size: <span></span>')
		    .find('span:last')
		    .radio(view_sizes, function(size) {
 			return size[0] + 'x' + size[1];
		    }, selected_size).bind('select', function(event, value) {
			var width = value[0];
			var height = value[1];
			$this.data(WIDTH, width).data(HEIGHT, height)
			    .find('.bin_view').trigger('drawBinDisplay');
			pageChanged(1);
		    });
		// add ROI scale controls
		// make the selected on checked
		var selected_scale = undefined;
		$.each(roi_scales, function(ix, scale) {
		    if(scale/100 == $this.data(ROI_SCALE)) {
			selected_scale = scale
		    }
		});
		$this.find('.view_controls').append('Scaling: <span></span>').find('span:last')
		    .radio(roi_scales, function(scale) {
			return scale + '%';
		    }, selected_scale).bind('select', function(event, value) {
			$this.data(ROI_SCALE, value/100)
			    .find('.bin_view').trigger('drawBinDisplay');
			pageChanged(1);
		    });
		// now add the bin display
		$this.append('<div class="bin_display"><div class="bin_links"></div></div>').find('.bin_display')
		    .css('float','left')
		// handle next / previous buttons
		$this.find('.bin_view_next_prev .nextBin')
		    .click(function() {
			$.getJSON('/'+timeseries+'/api/feed/after/pid/'+$this.data(PID), function(r) {
			    $this.trigger('goto_bin', [r[0].pid]);
			});
		    });
		$this.find('.bin_view_next_prev .previousBin')
		    .click(function() {
			$.getJSON('/'+timeseries+'/api/feed/before/pid/'+$this.data(PID), function(r) {
			    $this.trigger('goto_bin', [r[0].pid]);
			});
		    });
		// on redraw
		$this.bind('drawBinDisplay', function(event, the_pid, props) { 
		    // if the_pid is undefined, use whatever the pid was set to before
		    var pid = the_pid == undefined ? $this.data(PID) : the_pid;
		    // if there's no pid at this point
		    if(pid == undefined) {
			return; // there's nothing to do
		    }
		    if(props != undefined) {
			$this.data(HEIGHT, props.height == undefined ? $this.data(HEIGHT) : props.height);
			$this.data(WIDTH, props.width == undefined ? $this.data(WIDTH) : props.width);
			$this.data(ROI_SCALE, props.roiScale == undefined ? $this.data(ROI_SCALE) : props.roiScale);
		    }
		    $this.data(PID, pid); // save pid for future redraws
		    // get the selection and user preferred size/scale from the workspace
		    var roi_scale = $this.data(ROI_SCALE); // scaling factor per roi
		    var width = $this.data(WIDTH); // width of displayed view
		    var height = $this.data(HEIGHT); // height of displayed view
		    // create the bin display
		    $this.find('.bin_display')
			.mosaicPager(timeseries, pid, width, height, roi_scale);
		    $this.delegate('.bin_display','page_change', function(event, pageNumber, href, noChangeEvent) {
			pageChanged(pageNumber);
		    });
		    // delegate gotopage events to mosaic image pager
		    $this.bind('gotopage', function(event, page) {
			$this.find('.mosaic_pager_image_pager').trigger('gotopage', page);
			pageChanged(page);
		    });
		    // add bin links
		    $this.find('.bin_display')
			.append('<span><a href="'+pid+'.html">'+pid+'</a></span>')
			.append(' (<span class="imagepager_date timeago"></span>)<br>')
			.append('<span>Download: <a href="'+pid+'.adc">ADC</a></span>')
			.append('<span> <a href="'+pid+'.hdr">HDR</a></span>')
			.append('<span> <a href="'+pid+'.roi">ROI</a></span>')
			.append('<span> <a href="'+pid+'.csv">CSV</a></span>')
			.append('<span> <a href="'+pid+'.zip">ZIP</a></span>')
			.append('<span> <a href="'+pid+'.xml">XML</a></span>')
			.append('<span> <a href="'+pid+'.rdf">RDF</a></span>')
			.append('<span> <a href="'+pid+'_blob.zip">blobs ZIP</a></span>')
			.append('<span> <a href="'+pid+'_features.csv">features CSV</a></span>')
			.append('<span> <a href="'+pid+'_class_scores.csv">autoclass CSV</a></span>')
			.find('span').addClass('bin_label');
		});
	    });//each in resizableBinView
	}
    });//$.fn.extend
})(jQuery);//end of plugin
