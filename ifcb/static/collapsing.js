// jQuery UI plugin providing collapsing element
(function($) {
    $.fn.extend({
	collapsing: function(title) {
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		var state = 0;
		var e = $this.wrap('<div class="collapsing_content"></div>').parent()
		    .css('display','none')
		    .wrap('<div class="collapsing"></div>').parent();
		$(e).prepend('<div class="collapse_button collapse_button_closed">Show '+title+'</div>')
		    .find('.collapse_button')
		    .click(function() {
			console.log('clicked collapse button');
			if(state == 0) {
			    $(e).find('.collapse_button').removeClass('collapse_button_closed')
				.addClass('collapse_button_open')
				.empty().append('Hide '+title);
			    $(e).find('.collapsing_content').css('display','block');
			    state = 1;
			} else {
			    $(e).find('.collapse_button').removeClass('collapse_button_open')
				.addClass('collapse_button_closed')
				.empty().append('Show '+title);
			    $(e).find('.collapsing_content').css('display','none');
			    state = 0;
			}
		    });
	    });//each in collapsing
	}//collapsing
    });//$.fn.extend
})(jQuery);//end of plugin
