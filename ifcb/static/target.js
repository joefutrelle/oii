(function($) {
    $.fn.extend({
	target_image: function(target_pid, width, height) {
	    var image = target_pid + '.jpg'
	    var blob = target_pid + '_blob.png'
	    var labels = ['image', 'blob'];
	    var urls =    [image,   blob];
	    return this.each(function () {
		var $this = $(this); // retain ref to $(this)
		var view = 0;
		function update() {
		    $this.find('div.target_image').empty()
			.grayLoadingImage(urls[view], width, height)
			.append('shown: '+labels[view]+'. click for '+labels[(view+1)%urls.length]);
		}
		$this.append('<div class="target_image"></div>').find('div:last')
		    .css('width',width)
		    .css('height',height+20)
		    .click(function() {
			view = (view + 1) % urls.length;
			console.log('view = '+view);
			update();
		    });
		update();
	    });//each in bin_page
	}//bin_page
    });//$.fn.extend
})(jQuery);//end of plugin
