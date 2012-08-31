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
		$this.empty().append('<div/><p class="bin_label">'+pid+'</p>')
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
					$this.trigger('roi_click', [tile.pid, tile.width, tile.height]);
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
	}//mosaicPager
    });//$.fn.extend
})(jQuery);//end of plugin
