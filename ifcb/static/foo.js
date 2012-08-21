$(document).ready(function() {
    var images = [];
    var width=640;
    var height=480;
    for(page=1; page <= 30; page++) {
	images.push('/api/mosaic/size/'+width+'x'+height+'/scale/0.333/page/'+page+'/pid/IFCB5_2012_231_205056.jpg');
    }
    console.log(images);
    $('#main').append('<div class="wrapper"></div>').find('div').imagePager(images, width, height).change(function(event, href) {
	$('#url_label').empty().append(href);
    });
    $('#main').append('<div id="url_label"></div>');
});