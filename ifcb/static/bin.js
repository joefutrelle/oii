(function($) {
    $.fn.extend({
	bin_page: function(bin_pid) {
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		// style the tables on the page
		$('tr:even').addClass('tbl_even');
		// now add a resizable mosaic pager
		$this.empty()
		    .resizableMosaicPager()
		    .bind('roi_click', function(event, roi_pid) {
			window.location.href = roi_pid + '.html';
		    }).trigger('drawMosaic', [bin_pid])
	    });//each in bin_page
	}//bin_page
    });//$.fn.extend
})(jQuery);//end of plugin
