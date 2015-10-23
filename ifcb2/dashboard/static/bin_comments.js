(function($) {
    $.fn.extend({
        format_comment_body: function() {
            return this.each(function() {
                var comment_text = $(this).html();
                comment_text = comment_text.replace(/\n/g, '<br/>');
                $(this).empty().append(comment_text);
            });
        },
        append_comment: function(c, deletable, bin_pid, bin_lid) {
            return this.each(function() {
                var delete_control = '';
                if(deletable) {
                   delete_control = '<a class="close delete_comment"></a>';
                }
                var bin_link = '';
                if(bin_pid) {
                    bin_link = '<div class="comment_heading">'+
                        '<a href="'+bin_pid+'.html">'+bin_lid+'</a>'+
                    '</div>';
                }
                $(this).append('<div class="comment">'+
                    '<div class="comment_heading">'+delete_control+c.author+' commented '+
                        '<a href="'+c.bin_pid+'.html" class="comment_link">'+
                            '<span class="comment_ts timeago" title="'+c.ts+'">'+
                                c.ts+
                        '</span></a></div>'+
                        '<div class="comment_body">'+c.body+'</div>'+
                        bin_link+
                    '</div>').find('.timeago').timeago()
                    .end().find('.comment_body').format_comment_body();
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
        },
        timeseries_search: function(ts_label) {
            return this.each(function() {
                var $this = $(this);
                $this.empty().append('<input class="search"></input>'+
                    '<button class="search">Search</button><br/>'+
                    'Search <select class="search_target">'+
                        '<option>comments</option>'+
                        '<option>tags</option>'+
                    '</select>');
                $this.find('button.search').button().on('click', function() {
                    var query = $('input.search').val();
                    var target = $('select.search_target').val();
                    var url = '';
                    if(target=='comments') {
                        url = '/'+ts_label+'/search_comments?' + $.param({q:query});
                    } else {
                        query = query.replace(/ *, */g,'+');
                        url = '/'+ts_label+'/search_tags/' + query;
                    }
                    window.location.href = url;
                });
                var input = $this.find('input.search');
                var tmp = input.focus().val();
                input.val('').val(tmp);
                $(input).on('keyup',function(e) {
                    if(e.keyCode!=13) { return; }
                    $('button.search').click();
                });
            });
        }
    });//$.fn.extend
})(jQuery);//end of plugin
