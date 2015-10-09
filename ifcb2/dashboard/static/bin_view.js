(function($) {
    $.fn.extend({
        resizableBinView: function(timeseries, viewParams) {
            return this.each(function () {
                var $this = $(this); // retain ref to $(this)
                var PID = 'data_rbv_pid';
                var DATE = 'data_rbv_date';
                var VIEW_TYPE = 'data_rbv_view_type';
                var WIDTH = 'data_rbv_view_width';
                var HEIGHT = 'data_rbv_view_height';
                // initialization
                var view_types = ['mosaic','plot'];
                var view_sizes = [[640,480], [800,600], [1280,720], [1280,1280]];
                // FIXME initialize from view params
                var viewType = 'mosaic';
                var viewSize = [800,600];
                $this.data(WIDTH,viewSize[0]);
                $this.data(HEIGHT,viewSize[1]);
                function pageChanged(pageNumber) {
                    pageNumber == pageNumber ? pageNumber : 1;
                }
                // add next / previous controls
                $this.append('<div class="bin_view_next_prev"></div>')
                $this.find('.bin_view_next_prev')
                    .append('<span class="controlGray biggerText previousBin">&#x25C0; Previous</span>')
                    .append('<span class="controlGray biggerText"> | </span>')
                    .append('<span class="controlGray biggerText nextBin">Next &#x25B6;</span>');
                // add view type controls
                $this.append('<div class="bin_view_controls"></div>')
                    .find('.bin_view_controls')
                    .append('View: <span></span>')
                    .find('span:last')
                    .radio(view_types, function(viewType) {
                        return viewType;
                    }, viewType).bind('select', function(event, value) {
                        $this.data(VIEW_TYPE, value);
                        $this.trigger('drawBinDisplay');
                        pageChanged(1);
                    }).trigger('select',[viewType]); // allow view type to build itself
                // add view size controls
                $this.find('.bin_view_controls')
                    .append('View size: <span></span>')
                    .find('span:last')
                    .radio(view_sizes, function(size) {
                         return size[0] + 'x' + size[1];
                    }, viewSize).bind('select', function(event, value) {
                        var width = value[0];
                        var height = value[1];
                        $this.data(WIDTH, width).data(HEIGHT, height)
                            .trigger('drawBinDisplay');
                        pageChanged(1);
                    });
                // add view-type-specific controls
                $this.find('.bin_view_controls')
                    .append('<span class="bin_view_specific_controls"></span>')
                // now add the bin display
                $this.append('<div class="bin_display"></div>')
                    .append('<div class="bin_links"></div>')
                    .append('<div class="bin_actions biggerText"></div>')
                    .append('<div class="bin_tags biggerText"></div>')
                    .find('.bin_display')
                    .css('float','left')
                    .end().find('.bin_tags')
                    .css('width',$this.data(WIDTH));
                // handle next / previous buttons
                $this.find('.bin_view_next_prev .nextBin')
                    .click(function() {
                        $.getJSON('/'+timeseries+'/api/feed/after/pid/'+$this.data(PID), function(r) {
                            $this.trigger('goto_bin', [r[0].pid]);
                        });
                    });
                $this.find('.bin_view_next_prev .previousBin')
                    .click(function() {
                        $.getJSON('/'+timeseries+'/api/feed/before/pid/'+$this.data(PID), function(r) {
                            $this.trigger('goto_bin', [r[0].pid]);
                        });
                    });
                // draw bin event handler
                $this.bind('drawBinDisplay', function(event, the_pid) { 
                    // if the_pid is undefined, use whatever the pid was set to before
                    var pid = the_pid == undefined ? $this.data(PID) : the_pid;
                    // if there's no pid at this point
                    if(pid == undefined) {
                        return; // there's nothing to do
                    }
                    $this.data(PID, pid); // save pid for future redraws
                    $this.removeData(DATE); // clear date
                    // add bin links
                    $this.find('.bin_links')
                        .empty()
                        .append('<span><a href="'+pid+'.html">'+pid+'</a></span>')
                        .append(' (<span class="imagepager_date timeago"></span>)<br>')
                        .append('<span>Download: <a href="'+pid+'.adc">ADC</a></span>')
                        .append('<span> <a href="'+pid+'.hdr">HDR</a></span>')
                        .append('<span> <a href="'+pid+'.roi">ROI</a></span>')
                        .append('<span> <a href="'+pid+'.csv">CSV</a></span>')
                        .append('<span> <a href="'+pid+'.zip">ZIP</a></span>')
                        .append('<span> <a href="'+pid+'.xml">XML</a></span>')
                        .append('<span> <a href="'+pid+'.rdf">RDF</a></span>')
                        .append('<span> <a href="'+pid+'_blob.zip">blobs ZIP</a></span>')
                        .append('<span> <a href="'+pid+'_features.csv">features CSV</a></span>')
                        .append('<span> <a href="'+pid+'_class_scores.csv">autoclass CSV</a></span>')
                        .find('span').addClass('bin_label');
                    $this.find('.bin_actions');
                    // handle the total rois and timeago
                    $.getJSON(pid+'_medium.json', function(r) {
                        $this.find('.imagepager_rois_total').empty().append(r.targets.length+'');
                        $this.find('.imagepager_date').attr('title',r.date).timeago();
                        $this.data(DATE,r.date);
                    });
                    // if privileged, add bin actions
                    $.getJSON('/is_admin', function(r) {
                        $this.find('.bin_tags').editableBinTags(timeseries, pid);
                        $this.find('.bin_actions').empty()
                            .append('Actions: <span class="day_admin"></span> <span class="link skip"></span>')
                            .find('.skip').bin_skip(pid, true);
                        function create_day_link(date) {
                            $this.find('.bin_actions .day_admin').empty()
                                .append('<a href="/'+timeseries+'/api/feed/day_admin/'+date+'">Go to day</a>');
                        }
                        if($this.data(DATE) != undefined) {
                            create_day_link($this.data(DATE));
                        } else {
                            $.getJSON(pid+'_medium.json', function(r) {
                                create_day_link(r.date);
                                $this.data(DATE,r.date);
                            });
                        }
                    }).fail(function(r) { // not admin
                        $this.find('.bin_tags').binTags(timeseries, pid);
                    });
                    // get the selection and user preferred size/scale from the workspace
                    var viewType = $this.data(VIEW_TYPE); // view type
                    var width = $this.data(WIDTH); // width of displayed view
                    var height = $this.data(HEIGHT); // height of displayed view
                    if(viewType=="mosaic") {
                        // create the mosaic display
                        $this.find('.bin_display')
                            .empty()
                            .mosaicPager(timeseries, pid, width, height);
                        $this.delegate('.bin_display','page_change', function(event, pageNumber, href, noChangeEvent) {
                            pageChanged(pageNumber);
                        });
                        // delegate gotopage events to mosaic image pager
                        $this.bind('gotopage', function(event, page) {
                            $this.find('.mosaic_pager_image_pager').trigger('gotopage', page);
                            pageChanged(page);
                        });
                    } else if(viewType=='plot') {
                        $this.find('.bin_display')
                            .empty()
                            .scatter(timeseries, pid, width, height);
                    }
                });
            });//each in resizableBinView
        }
    });//$.fn.extend
})(jQuery);//end of plugin
