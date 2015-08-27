(function($) {
    $.fn.extend({
        bin_skip: function(pid, require_confirm) {
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		var EVENT='bin_skip_get_flag';
		$this.on(EVENT, function() {
		    $.getJSON('/api/get_skip/'+pid,function(r) {
			if(r.skip) {
			    $this.empty().append('(skipped: <span class="pseudolink">unskip</a>)')
				.off('click').on('click unskip_bin',function() {
				    $.getJSON('/api/unskip/'+pid, function(r) {
					$this.trigger(EVENT);
				    });
				});
			} else {
			    $this.empty().append('(active: <span class="pseudolink">skip</a>)')
				.off('click').on('click skip_bin',function() {
				    var confirmed = true;
				    if(require_confirm) {
					confirmed = confirm('Are you sure you want to skip '+pid+'?');
				    }
				    if(confirmed) {
					$.getJSON('/api/skip/'+pid, function(r) {
					    $this.trigger(EVENT);
					});
				    }
				});
			}
		    });//request to /api/get_skip
		}).trigger(EVENT);// initial trigger
	    });//this.each in bin_skip
	}//bin_skip
    });//$.fn.extend
})(jQuery);//end of plugin
