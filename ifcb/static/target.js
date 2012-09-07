(function($) {
    $.fn.extend({
	target_image: function(target_pid, width, height) {
	    var image = target_pid + '.jpg'
	    var blob = target_pid + '_blob.png'
	    var outline = target_pid + '_blob_outline.png'
	    var labels = ['image', 'blob', 'outline'];
	    var urls =    [image,   blob,   outline];
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		var view = 0;
		function update() {
		    $this.find('div.target_image').empty()
			.grayLoadingImage(urls[view], width, height)
			.end().find('div.target_image_text').empty()
			.append('shown: '+labels[view]+'. click for '+labels[(view+1)%urls.length]);
		}
		var e = $this.append('<div></div>').find('div:last');
		$(e).append('<div></div>').find('div:last').addClass('target_image')
		    .css('width',width)
		    .css('height',height)
		    .click(function() {
			view = (view + 1) % urls.length;
			console.log('view = '+view);
			update();
		    });
		$(e).append('<div></div>').find('div:last').addClass('target_image_text');
		$(e).append('<div>&#x25B6; Show metadata</div>').find('div:last').addClass('collapse')
		    .css('text-align','left')
		    .css('color','gray')
		    .click(function() {
			var display = $(e).find('div.metadata').css('display') == 'block' ? 'none' : 'block';
			if(display == 'none') {
			    $(e).find('div.collapse').empty().append('&#x25B6; Show metadata</div>');
			} else {
			    $(e).find('div.collapse').empty().append('&#x25BC; Hide metadata</div>');
			}
			$this.find('div.metadata').css('display',display);
		    });
		$(e).append('<div></div>').find('div:last').addClass('metadata')
		    .css('display','none')
		    .css('text-align','left');
		$.getJSON(target_pid+'.json', function(r) {
		    for(var key in r) {
			$(e).find('div.metadata')
			    .append('<div><span class="metadata_key">'+key+'</span> <span class="metadata_value">'+r[key]+'</span></div>');
		    }
		});
		update();
	    });//each in bin_page
	}//bin_page
    });//$.fn.extend
})(jQuery);//end of plugin
