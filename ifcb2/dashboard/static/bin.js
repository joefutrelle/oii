(function($) {
    $.fn.extend({
        bin_page: function(bin_pid, timeseries) {
            return this.each(function () {
                var $this = $(this); // retain ref to $(this)
                // now add a resizable bin view
                $this.empty()
                    .resizableBinView(timeseries)
                    .bind('roi_click', function(event, roi_pid) {
                        window.location.href = roi_pid + '.html';
                    }).trigger('drawBinDisplay', [bin_pid]);
                    // caller must bind goto_bin
            });//each in bin_page
        },//bin_page
        bin_files: function(bin_pid, time_series) {
            return this.each(function() {
                var $this = $(this);
                $this.empty()
                    .append('<div class="major inline fixity_container" style="display:none">'+
                                '<table class="fixity_table">'+
                                    '<tr class="tbl">'+
                                      '<th class="tbl">filename</th>'+
                                      '<th class="tbl">length</th>'+
                                      '<th class="tbl">sha1</th>'+
                                      '<th class="tbl">fixed</th>'+
                                      '<th class="tbl">local path</th>'+
                                      '<th class="tbl">status</th>'+
                                    '</tr>'+
                                '</table>'+
                            '</div>');
                $.getJSON('/'+time_series+'/api/files/'+bin_pid,function(r) {
                    $.each(r, function(ix, f) {
                        $this.find('.fixity_table').append('<tr class="tbl">'+
                            '<td class="tbl"><a href="/'+time_series+'/'+f.filename+'">'+f.filename+'</a></td>'+
                            '<td class="tbl" title="'+f.length+'">'+filesize(f.length)+'</td>'+
                            '<td class="tbl">'+f.sha1+'</td>'+
                            '<td class="tbl">'+f.fix_time+'</td>'+
                            '<td class="tbl">'+f.local_path+'</td>'+
                            '<td class="tbl">'+
                            (f.check.exists?'exists':'does not exist')+', '+
                            (f.check.length?'length matches':'length does not match')+' '+
                            '</td>'+
                        '</tr>');
                    });
                    $this.find('.fixity_table tr:even').addClass('tbl_even');
                    $this.find('.fixity_table').collapsing('files',1);
                    $this.find('.fixity_container').css('display','inline-block');
                });//AJAX call
            });//this.each in bin_files
        },//bin_files
        bin_metadata: function(bin_pid, time_series) {
            return this.each(function() {
                var $this = $(this);
                $this.empty()
                    .append('<div class="bin_metadata_container major inline">'+
                                '<div><b class="bin_date"></b> '+
                                '(<a href="/'+time_series+'/dashboard/'+bin_pid+'">Show in time series</a>)</div>'+
                                '<div class="bin_metadata"></div>'+
                            '</div>');
                $.getJSON(bin_pid+'_short.json',function(r) {
                    $this.find('.bin_date').empty().append(r.date);
                    $this.find('.bin_metadata').append('<div class="metadata_key">context</div>');
                    $.each(r.context, function(ix, v) {
                        $this.find('.bin_metadata')
                            .append('<span class="metadata_value">'+v+'</span>');
                    });
                    for(k in r) {
                        if(k!='context' && r.hasOwnProperty(k)) {
                            $this.find('.bin_metadata')
                                .append('<div>'+
                                            '<span class="metadata_key">'+k+'</span> '+
                                            '<span class="metadata_value">'+r[k]+'</span>'+
                                        '</div>')
                        }
                    }
                    $this.find('.bin_metadata').collapsing('metadata',0);
                });
            });//each in bin_metadata
        },//bin_metadata
        bin_targets: function(bin_pid) {
            return this.each(function() {
                var $this = $(this);
                $this.empty()
                    .append('<div class="major inline">'+
                                '<table class="targets_table">'+
                                    '<tr class="tbl">'+
                                      '<th class="tbl">#/trigger</th>'+
                                      '<th class="tbl">pid</th>'+
                                      '<th class="tbl">size</th>'+
                                    '</tr>'+
                                '</table>'+
                            '</div>');
                $.get(bin_pid+'_targetstable',function(r) {
                    $this.find('.targets_table').append(r);
                    $this.find('.targets_table tr:even').addClass('tbl_even');
                });
                $this.find('.targets_table').collapsing('targets',1);
            });
        }//bin_targets
    });//fn.extend
})(jQuery);//end of plugin
