// jQuery plugin for paging through a list of images
// give it a list of images and an image size and it will
// create a pager in whatever element you call this on.
// To recieve change events bind for change events like this:
// $.change(function(event, image_href) {
//    ... do something image_href ...
// });
(function($) {
    function grayLoadingImage(node, image_href, width, height) {
	$(node).empty()
	    .append('<div></div>').find('div').addClass('imagepager_frame')
	    .css('width',width).css('height',height)
	    .css('overflow','hidden')
	    .append('<img><div></div>')
	    .find('div:last').addClass('imagepager_placeholder')
	    .css('width',width).css('height',height)
	    .end()
	    .find('img')
	    .css('display','none')
            .addClass('page_image')
	    .addClass('imagepager_nodisplay')
	    .attr('src',image_href)
	    .load(function() {
		$(node).find('.imagepager_placeholder').remove()
		    .end()
		    .find('img')
		    .attr('width',width).attr('height',height)
		    .css('display','block');
		console.log('loaded '+image_href);
	    });
    }
    $.fn.extend({
	grayLoadingImage: function(image_href, width, height) {
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		grayLoadingImage($this, image_href, width, height);
	    });
	},
	imagePager: function(image_list, width, height, offset) {
	    // offset defaults to 0
	    offset = typeof offset !== 'undefined' ? offset : 0;
	    var ix = offset;
	    // image_list - a list of image URLs
	    // width -  the width  \__to scale the images to
	    // height - the height / 
	    // offset - zero-based image to start on
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		var gli = $this.append('<div></div>')
		    .append('<div></div>')
		    .append('<div></div>')
		    .find('div').css('display','inline-block')
		    .end()
		    .find('div:first').css('height',height).addClass('imagepager_arrow imagepager_left')
		    .end()
		    .find('div:last').css('height',height).addClass('imagepager_arrow imagepager_right')
		    .end().css('clear','both')
		    .find('div:eq(1)')
		function showImage() {
		    var image_href = image_list[ix];
		    grayLoadingImage($(gli), image_href, width, height);
		    // defer in case this is the first showImage
		    // and clients are still waiting to attach event handlers
		    setTimeout(function() {
			$this.trigger('change', image_href);
		    }, 0);
		}
		$this.find('.imagepager_left').click(function() {
		    if(ix > 0) {
			ix--;
			showImage();
		    }
		});
		$this.find('.imagepager_right').click(function() {
		    if(ix < image_list.length -1) {
			ix++;
			showImage();
		    }
		});
		showImage();
	    });//each in imagePager
	}//imagePager
    });//$.fn.extend
})(jQuery);//end of plugin
