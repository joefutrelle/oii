// jQuery UI plugin providing locking content
// wraps and puts lock control at upper right
// will start locked if initial_state is logical true otherwise unlocked
// when lock control is toggled to lock, calls lock callback
// when lock control is toggled to unlock, calls unlock callback
// will call callback based on initial state!
(function($) {
    $.fn.extend({
	locking: function(lock_callback, unlock_callback, initial_state) {
	    function callback_for(state) {
		state ? lock_callback() : unlock_callback();
            }
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		var initial_state_class = initial_state ? 'ui-icon-locked' : 'ui-icon-unlocked';
		var e = $this.prepend('<span class="lockcontrol ui-button-icon-primary ui-icon '+initial_state_class+'"></span></div>').parent();
		$(e).find('.lockcontrol')
		    .click(function() {
			var state = $(this)
			    .toggleClass('ui-icon-locked ui-icon-unlocked')
			    .hasClass('ui-icon-locked');
			callback_for(state);
		    });
		callback_for(initial_state);
	    });//each in collapsing
	}//collapsing
    });//$.fn.extend
})(jQuery);//end of plugin
