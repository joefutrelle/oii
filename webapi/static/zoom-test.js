var scale = 0.2;
var rotate = 0;
$(document).ready(function() {
    var imageUrl = 'http://www.schneertz.com/schneertzHD.png';
    $('#cell').prepend('<div id="debug">&nbsp;</div>');
    $('#cell').prepend('<img style="display:none" src="' + imageUrl + '">').find('img').bind('load', {
        cell : cell
    }, function(event) {
        var image = this;
        var imageWidth = $(image).width();
        var imageHeight = $(image).height();
        var canvasWidth = 200;
        var canvasHeight = 200;
        var canvas = $(cell).append('<canvas width="' + canvasWidth + 'px" height="' + canvasHeight + 'px"></canvas>')
            .find('canvas:last');
        var ctx = canvas[0].getContext('2d');
        var debugCanvas = $(cell).append('<canvas width="'+imageWidth+'px" height="'+imageHeight+'px"></canvas>')
            .find('canvas:last');
        var debugCtx = debugCanvas[0].getContext('2d');
        ctx.strokeStyle = '#f00';
        debugCtx.strokeStyle = '#f00';
        var env = {
            image: image,
            canvas : canvas,
            ctx : ctx,
            debugCanvas: debugCanvas,
            debugCtx: debugCtx
        };
        var centerX = imageWidth / 2;
        var centerY = imageHeight / 2;
        $(cell).bind('mousedown', env, function(event) {
            var image = event.data.image;
            var ctx = event.data.ctx;
            var debugCtx = event.data.debugCtx;
            var sourceX = centerX - ((canvasWidth / scale) / 2);
            var sourceY = centerY - ((canvasHeight / scale) / 2);
            var sourceWidth = canvasWidth / scale;
            var sourceHeight = canvasHeight / scale;
            // capture mouse click relative to canvas origin in canvas space
            var x = mouseX(event, canvas);
            var y = mouseY(event, canvas);
            // translate/scale "inverted" mouse click to original image space
            var clickX = sourceX + ((1.0 - (x / canvasWidth)) * sourceWidth);
            var clickY = sourceY + ((1.0 - (y / canvasHeight)) * sourceHeight);
            debugCtx.drawImage(image, 0, 0, imageWidth, imageHeight);
            debugCtx.strokeRect(sourceX, sourceY, sourceWidth, sourceHeight);
            debugCtx.strokeRect(clickX-5,clickY-5,10,10);
            ctx.drawImage(image,sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, canvasWidth, canvasHeight);
            ctx.strokeRect(x-5,y-5,10,10);
            // recenter sourceXY around new origin of clickXY
            sourceX -= clickX;
            sourceY -= clickY;
            var zoomFactor = 1.1;
            // now scale source by zoom factor
            sourceX *= zoomFactor;
            sourceY *= zoomFactor;
            sourceWidth *= zoomFactor;
            sourceHeight *= zoomFactor;
            // restore old origin of clickX, clickY 
            sourceX += clickX;
            sourceY += clickY;
            // now compute the new center
            centerX = sourceX + (sourceWidth / 2);
            centerY = sourceY + (sourceHeight / 2);
            clog('-> cx=' + centerX + ', cy=' + centerY);
            ctx.drawImage(image,sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, canvasWidth, canvasHeight);
            // compute new scale
            scale = scale * zoomFactor;
            debugCtx.strokeStyle = '#f00';
            debugCtx.strokeRect(sourceX, sourceY, sourceWidth, sourceHeight);
            debugCtx.strokeRect(clickX-5,clickY-5,10,10);
        });
    });
});