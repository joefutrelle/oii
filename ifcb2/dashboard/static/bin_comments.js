(function($) {
    $.fn.extend({
        bin_comments: function(bin_pid) {
            return this.each(function() {
                var $this = $(this);
                var refresh_comments = function() {
                    $.getJSON('/api/comments_editable/'+bin_pid, function(r) {
                        $this.empty();
                        $.each(r.comments, function(ix, c) {
                            var button_elt = '';
                            if(c.deletable) {
                                button_elt = '<button class="delete_comment">Delete</button>';
                            }
                            $this.append('<div class="comment">'+
                                '<div class="comment_author">'+c.author+'</div>'+
                                '<div class="comment_ts timeago" title="'+c.ts+'">'+c.ts+'</div>'+
                                '<div class="comment_body">'+c.body+'</div>'+
                                button_elt+
                            '</div>').find('.timeago').timeago()
                            .end().find('.comment:last .delete_comment').on('click', function() {
                                if(confirm('really delete this comment?')) {
                                    $.getJSON('/api/delete_comment/'+c.id, function() {
                                        refresh_comments();
                                    });
                                }
                            });
                        });
                        if(r.addable) {
                            $this.append('<div class="comment">'+
                                '<input id="new_comment_body" type="text">'+    
                                '<button class="add_comment">Add comment</button>'+
                            '</div>').find('button.add_comment').on('click', function() {
                                var body = $('#new_comment_body').val();
                                $.post('/api/add_comment/'+bin_pid, { body: body }, function() {
                                    refresh_comments();
                                });
                            });
                        }
                    });
                };
                refresh_comments();
            });
        }
    });//$.fn.extend
})(jQuery);//end of plugin
