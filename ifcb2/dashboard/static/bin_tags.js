(function($) {
    $.fn.extend({
        // add a tag-styled tag with link
        addTag: function(ts_label, tag) {
            return this.each(function() {
                var href = '/'+ts_label+'/search_tags/'+tag;
                var a = '<a href="'+href+'" class="tag_link">'+tag+'</a>';
                $(this).append('<div class="tag inline">'+a+'</div>');
            });
        },
        // add a "+" button and attach click handler
        _tags_addableTag: function(clk) {
            return this.each(function() {
                $(this).empty().prepend('<a class="addable_tag"></a>');
                $(this).on('click', clk);
            })
        },
        // non-editable tags
        binTags: function(ts_label, pid) {
            return this.each(function() {
                var $this = $(this);
                $this.empty();
                // get tags from the server and show as non-editable
                $.getJSON('/'+ts_label+'/api/tags/'+pid, function(r) {
                    if(r.length==0) { return; }
                    $this.empty().append('Tags:');
                    // add an inline tag-styled div per tag
                    $.each(r, function(ix, tag) {
                        $this.addTag(ts_label, tag);
                    });
                });
            });
        },
        editableBinTags: function(ts_label, pid) {
            return this.each(function() {
                var $this = $(this);
                $this.empty();
                // get tags from server and show as editable
                var refresh_tags = function(df) {
                    $.getJSON('/'+ts_label+'/api/tags/'+pid, function(r) {
                        $this.empty().append('Tags:');
                        // add an inline editable-tag-styled div per tag
                        $.each(r, function(ix, tag) {
                            $this.addTag(ts_label, tag)
                                // add an X button that deletes the tag
                                .find('.tag:last')
                                .prepend('<a class="removeable_tag"></a>')
                                .find('.removeable_tag').on('click', function() {
                                    console.log('user clicked x on '+tag);//FIXME debug
                                    // X clicked; delete the tag
                                    $.getJSON('/'+ts_label+'/api/remove_tag/'+tag+'/'+pid, function() {
                                        // reload tags from server
                                        refresh_tags();
                                    });
                                });
                        });
                        // put a text box in the last div for user to enter a new tag
                        var openForEditing = function() {
                            $this.find('.add_tag')
                                .empty()
                                // add a text box
                                .append('<input type="text"></input>')
                                // and an X button to close
                                .append(' <a class="close_new_tag removeable_tag"></a>')
                                .find('.close_new_tag')
                                .on('click', function() {
                                    // user clicked X button, cancel
                                    refresh_tags();
                                })
                                .prev().focus()
                                // enter key in text area adds tag
                                .on('keyup', function(e) {
                                    if(e.keyCode != 13) { return; }
                                    // get the text of the tag from the text box
                                    var tag = $(this).val().trim();
                                    if(!tag) { refresh_tags(); } // user typed nothing, cancel
                                    else {
                                        // add the tag on the server
                                        $.getJSON('/'+ts_label+'/api/add_tag/'+tag+'/'+pid, function() {
                                            // reload tags from server
                                            refresh_tags(function() {
                                                // and click "+" to add another tag
                                                $this.find('a.addable_tag').trigger('click');
                                            });
                                        });
                                    }
                                }).on('focusout', function() {
                                    // user focused out, close the text box
                                    closeForEditing();
                                });
                        };//openForEditing
                        // set up a "+" button that will open for editing
                        var closeForEditing = function() {
                            $this.find('.add_tag')._tags_addableTag(function() {
                                openForEditing();
                            });
                        };
                        // add a "+" button
                        $this.append('<div class="tag inline add_tag"></div>');
                        // close it for editing
                        closeForEditing();
                        // run deferred function now that we have refreshed tags
                        if(df) {
                            df();
                        }
                    });
                }//refresh_tags
                // entry point of editableBinTags
                // initially, refresh tags
                refresh_tags();
            });//this.each
        }//editableBinTags
    });//$.fn.extend
})(jQuery);//end of plugin
