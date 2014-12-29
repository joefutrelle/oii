(function($) {
    $.fn.extend({
	bin_page: function(bin_pid, timeseries) {
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		// style the tables on the page
		$('tr:even').addClass('tbl_even');
		// now add a resizable bin view
		$this.empty()
		    .resizableBinView(timeseries)
		    .bind('roi_click', function(event, roi_pid) {
			window.location.href = roi_pid + '.html';
		    }).bind('goto_bin', function(event, bin_pid) {
			window.location.href = bin_pid + '.html';
		    }).trigger('drawBinDisplay', [bin_pid])
	    });//each in bin_page
	}//bin_page
    });//$.fn.extend
})(jQuery);//end of plugin
