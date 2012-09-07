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
		$(e).append('<div class="target_metadata"></div>').find('div:last')
		    .target_metadata(target_pid).collapsing('metadata')
		update();
	    });//each in target_image
	},//target_image
	target_metadata: function(target_pid) {
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		$.get(target_pid+'.xml', function(x) {
		    $(x).find('Target *').each(function(ix, thang) {
			var key = $(thang).get(0).tagName;
			var value = $(thang).text();
			console.log(key+'='+value);
			$this.append('<div><span class="metadata_key">'+key+'</span> '+
				    '<span class="metadata_value">'+value+'</span></div>');
		    });
		});
	    });//each in target_metadata
	}//target_metadata
    });//$.fn.extend
})(jQuery);//end of plugin
