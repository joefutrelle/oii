(function($) {
    $.fn.extend({
        bin_skip: function(pid, require_confirm, initial_state) {
            return this.each(function () {
                var $this = $(this); // retain ref to $(this)
                var EVENT='bin_skip_get_flag';
                var showSkipped = function() {
                    $this.empty().append('(skipped: <span class="pseudolink">unskip</a>)')
                        .off('click').on('click unskip_bin',function() {
                            $.getJSON('/api/unskip/'+pid, function(r) {
                                $this.trigger(EVENT);
                            });
                        });
                };
                var showActive = function() {
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
                };
                $this.on(EVENT, function() {
                    $.getJSON('/api/get_skip/'+pid,function(r) {
                        if(r.skip) {
                            showSkipped();
                        } else {
                            showActive();
                        }
                    });//request to /api/get_skip
                });
                if(initial_state == undefined) {
                    $this.trigger(EVENT);
                } else if(initial_state == true) { // skipped
                    showSkipped();
                } else if(initial_state == false) { // active
                    showActive();
                }
            });//this.each in bin_skip
        }//bin_skip
    });//$.fn.extend
})(jQuery);//end of plugin
