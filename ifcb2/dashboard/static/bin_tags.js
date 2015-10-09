(function($) {
    $.fn.extend({
       removeableTag: function(clk) {
           return this.each(function () {
               var $this = $(this); // retain ref to $(this)
               $this.prepend('<a class="removeable_tag"></a>').find('a:first')
                   .css('cursor','pointer')
                   .bind('click', clk);
           });
       },
       addTag: function(clk) {
           return this.each(function() {
               var $this = $(this);
               $this.prepend('<a class="addable_tag"></a>').find('a:first')
                    .css('cursor','pointer')
                    .on('click', clk)
            })
        },
        binTags: function(ts_label, pid) {
            return this.each(function() {
                var $this = $(this);
                $this.empty();
                $.getJSON('/'+ts_label+'/api/tags/'+pid, function(r) {
                    if(r.length==0) { return; }
                    $this.empty().append('Tags:');
                    $.each(r, function(ix, tag) {
                        $this.append('<div class="tag inline">'+tag+'</div>');
                    });
                });
            });
        },
        editableBinTags: function(ts_label, pid) {
            return this.each(function() {
                var $this = $(this);
                $this.empty();
                var refresh_tags = function(df) {
                    $.getJSON('/'+ts_label+'/api/tags/'+pid, function(r) {
                        $this.empty().append('Tags:');
                        $.each(r, function(ix, tag) {
                            $this.append('<div class="tag inline">'+tag+'</div>')
                                .find('.tag:last').removeableTag(function() {
                                    $.getJSON('/'+ts_label+'/api/remove_tag/'+tag+'/'+pid, function() {
                                        refresh_tags();
                                    });
                                });
                        });
                        $this.append('<div class="tag inline add_tag"></div>')
                            .find('.tag:last').addTag(function() {
                                $this.find('.add_tag').empty()
                                .append('<input type="text"></input> <a class="close_new_tag removeable_tag"></a>')
                                .find('a:last').css('cursor','pointer').on('click', function() {
                                    refresh_tags();
                                })
                                .prev().focus().on('keyup', function(e) {
                                    if(e.keyCode != 13) {
                                        return;
                                    }
                                    var tag = $(this).val().trim();
                                    if(!tag) {
                                        refresh_tags();
                                    } else {
                                        $.getJSON('/'+ts_label+'/api/add_tag/'+tag+'/'+pid, function() {
                                            refresh_tags(function() {
                                                $('a.addable_tag').trigger('click');
                                            });
                                        });
                                    }
                                });
                            });
                        if(df) {
                            df();
                        }
                    });
                }//refresh_tags
                refresh_tags();
            });//this.each
        }//editableBinTags
    });//$.fn.extend
})(jQuery);//end of plugin
