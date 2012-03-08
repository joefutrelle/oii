var scale = 0.2;
var rotate = 0;
$(document).ready(function() {
    var imageUrl = 'http://www.schneertz.com/schneertzHD.png';
    $('#cell').prepend('<div id="debug">&nbsp;</div>');
    $('#cell').prepend('<img style="display:none" src="'+imageUrl+'">')
        .find('img')
        .bind('load', {
            cell: cell
        }, function(event) {
	    var image = this;
            var imageWidth = $(image).width();
            var imageHeight = $(image).height();
	    var canvasWidth = 200;
	    var canvasHeight = 200;
	    var canvas = $(cell).append('<canvas width="'+canvasWidth+'px" height="'+canvasHeight+'px" class="atorigin"></canvas>').find('canvas');
	    var ctx = canvas[0].getContext('2d');
	    var env = { canvas: canvas, ctx: ctx };
	    var centerX = imageWidth/2;
	    var centerY = imageHeight/2;
	    $(cell).bind('mousedown', env, function(event) {
		var sourceX = centerX - ((canvasWidth/scale)/2);
		var sourceY = centerY - ((canvasHeight/scale)/2);
		var sourceWidth = canvasWidth/scale;
		var sourceHeight = canvasHeight/scale;
		// capture mouse click relative to canvas origin in canvas space
		var x = mouseX(event, canvas);
		var y = mouseY(event, canvas);
		// translate/scale mouse click to original image space
		var clickX = sourceX + ((x/canvasWidth)*sourceWidth);
		var clickY = sourceY + ((y/canvasHeight)*sourceHeight);
		// recenter sourceXY around new origin of clickXY
		sourceX -= clickX;
		sourceY -= clickY;
		var zoomFactor = 1.1;
		// now scale source by zoom factor
		sourceX *= zoomFactor;
		sourceY *= zoomFactor;
		sourceWidth *= zoomFactor;
		sourceHeight *= zoomFactor;
		// translate sourceXY back to original image space
		sourceX += clickX;
		sourceY += clickY;
		// now compute the new center
		centerX = sourceX + (sourceWidth/2);
		centerY = sourceY + (sourceHeight/2);
		clog('-> cx='+centerX+', cy='+centerY);
		// compute new scale
		scale = scale * zoomFactor;
		var ctx = event.data.ctx;
		ctx.drawImage(image,sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, canvasWidth, canvasHeight);
	    });
        });
});