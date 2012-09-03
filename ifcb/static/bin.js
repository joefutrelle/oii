(function($) {
    $.fn.extend({
	bin_page: function(bin_pid) {
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		$this.empty()
		    .resizableMosaicPager()
		    .trigger('drawMosaic', [bin_pid]);
	    });//each in bin_page
	}//bin_page
    });//$.fn.extend
})(jQuery);//end of plugin
