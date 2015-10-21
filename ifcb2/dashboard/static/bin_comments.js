(function($) {
    $.fn.extend({
        append_comment: function(c, deletable) {
            return this.each(function() {
                var delete_control = '';
                if(deletable) {
                   delete_control = '<a class="close delete_comment"></a>';
                }
                $(this).append('<div class="comment">'+
                    '<div class="comment_heading">'+delete_control+c.author+' commented '+
                        '<a href="'+c.bin_pid+'.html" class="comment_link">'+
                            '<span class="comment_ts timeago" title="'+c.ts+'">'+
                                c.ts+
                        '</span></a></div>'+
                        '<div class="comment_body">'+c.body+'</div>'+
                    '</div>').find('.timeago').timeago();
            });
        },
        bin_comments: function(bin_pid) {
            return this.each(function() {
                var $this = $(this);
                var refresh_comments = function() {
                    $.getJSON('/api/comments_editable/'+bin_pid, function(r) {
                        $this.empty();
                        $.each(r.comments, function(ix, c) {
                            var cid = c.id;
                            $this.append_comment(c, c.deletable);
                            $this.find('.comment:last .delete_comment').on('click', function() {
                                if(confirm('Really delete this comment?')) {
                                    $.getJSON('/api/delete_comment/'+cid, function() {
                                        refresh_comments();
                                    });
                                }
                            });
                        });
                        if(r.addable) {
                            $this.append('<div>'+
                                '<div>'+
                                   '<textarea class="new_comment_body" rows="5" placeholder="Leave a comment"></textarea>'+ 
                                '</div>'+
                                '<button class="add_comment">Add comment</button>'+
                            '</div>').find('button.add_comment').button().on('click', function() {
                                var body = $this.find('.new_comment_body').val();
                                $.post('/api/add_comment/'+bin_pid, { body: body }, function() {
                                    refresh_comments();
                                });
                            }).end().find('textarea').focus();
                        }
                    });
                };
                refresh_comments();
            });
        }
    });//$.fn.extend
})(jQuery);//end of plugin
