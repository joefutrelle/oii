// jQuery plugin extending image_pager for IFCB mosaic images.
// obv requires image_pager.
// fires the following events
// page_change(page_url) - when the user changes the page; generally not used
// roi_click(roi_pid, width, height) - when the user clicks a ROI
(function($) {
    $.fn.extend({
	mosaicPager: function(pid, width, height, roi_scale) {
	    var BIN_URL='mosaic_bin_url';
	    // pid - bin pid (or lid)
	    // width -  the width  \__of the mosaic
	    // height - the height / 
	    // roi_scale - scale factor for ROIs
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		// put 30 pages on the pager, just in case it's a huge bin
		var images = [];
		for(var page=1; page <= 30; page++) {
		    // each page is a mosaic API call URL with a successive page number
		    var url = '/api/mosaic/size/'+width+'x'+height+'/scale/'+roi_scale+'/page/'+page+'/pid/'+pid+'.jpg';
		    images.push(url);
		}
		// list of images in hand, create the image pager
		$this.empty().append('<div></div>')
		    .append('<span class="bin_label"><a href="'+pid+'.html">'+pid+'</a></span>')
		    .append('<span> <a href="'+pid+'.adc">ADC</a></span>')
		    .append('<span> <a href="'+pid+'.hdr">HDR</a></span>')
		    .append('<span> <a href="'+pid+'.roi">ROI</a></span>')
		    .append('<span> <a href="'+pid+'.csv">CSV</a></span>')
		    .append('<span> <a href="'+pid+'.xml">XML</a></span>')
		    .append('<span> <a href="'+pid+'.rdf">RDF</a></span>')
		    .find('div:last').imagePager(images, width, height) // use the image pager plugin
		    .bind('change', function(event, image_href) { // when the user changes which page they're viewing
			$this.data(BIN_URL, image_href);
			$this.trigger('page_change', image_href);
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
        resizableMosaicPager: function(width, height, roi_scale, pid) {
	    var PID = 'mosaic_pager_bin_pid';
	    var WIDTH = 'mosaic_pager_width';
	    var HEIGHT = 'mosaic_pager_height';
	    var ROI_SCALE = 'mosaic_pager_roi_scale';
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		// store user preferences in data
		$this.data(PID, pid);
		$this.data(WIDTH, width == undefined ? 800 : width);
		$this.data(HEIGHT, height == undefined ? 600 : height);
		$this.data(ROI_SCALE, roi_scale == undefined ? 0.33 : roi_scale);
		// add some controls for changing the size of the mosaic
		var mosaic_sizes = [[640, 480], [800, 600], [1280, 720], [1280, 1280]];
		var roi_scales = [15, 25, 33, 40, 66, 100];
		// add size controls
		$this.append('<div class="mosaic_controls"></div>').find('.mosaic_controls')
		    .append('Mosaic size: <span></span>').find('span:last')
		    .radio(mosaic_sizes, function(size) {
 			return size[0] + 'x' + size[1];
		    }).bind('select', function(event, value) {
			var width = value[0];
			var height = value[1];
			$this.data(WIDTH, width).data(HEIGHT, height)
			    .find('.mosaic_pager').trigger('drawMosaic');
		    });
		// add ROI scale controls
		$this.find('.mosaic_controls').append('ROI scaling: <span></span>').find('span:last')
		    .radio(roi_scales, function(scale) {
			return scale + '%';
		    }).bind('select', function(event, value) {
			$this.data(ROI_SCALE, value/100)
			    .find('.mosaic_pager').trigger('drawMosaic');
		    });
		// now add the mosaic pager
		$this.append('<div class="mosaic_pager"></div>').find('.mosaic_pager')
		    .css('float','left'); // FIXME remove
		// on redraw
		$this.bind('drawMosaic', function(event, the_pid) { 
		    // if the_pid is undefined, use whatever the pid was set to before
		    var pid = the_pid == undefined ? $this.data(PID) : the_pid;
		    // if there's no pid at this point
		    if(pid == undefined) {
			return; // there's nothing to do
		    }
		    $this.data(PID, pid); // save pid for future redraws
		    // get the selection and user preferred size/scale from the workspace
		    var roi_scale = $this.data(ROI_SCALE); // scaling factor per roi
		    var width = $this.data(WIDTH); // width of displayed mosaic
		    var height = $this.data(HEIGHT); // height of displayed mosaic
		    // create the mosaic pager
		    $this.find('.mosaic_pager')
			.mosaicPager(pid, width, height, roi_scale);
		});
	    });//each in resizableMosaicPager
	}
    });//$.fn.extend
})(jQuery);//end of plugin
