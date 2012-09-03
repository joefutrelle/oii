function show_bin_page(bin_pid) {
    $('body').append('<div></div>')
	.find('div')
	.resizableMosaicPager()
	.trigger('drawMosaic', [bin_pid]);
}