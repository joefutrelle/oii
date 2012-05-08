// globals (FIXME: make preferences)
var scalingFactor = 1;
var geometryColor = '#f00';
// geometric tool support
var geometry = {};
geometry.boundingBox = {
    label: 'Bounding box',
    draw: function(ctx, boundingBox) {
        var left = scalingFactor * boundingBox[0][0];
        var top = scalingFactor * boundingBox[0][1];
        var right = scalingFactor * boundingBox[1][0]; 
        var bottom = scalingFactor * boundingBox[1][1];
        ctx.strokeStyle = geometryColor;
        ctx.strokeRect(left, top, right-left, bottom-top);
    },
    prepareForStorage: function(annotation) {
        return unscaleAnnotation(this, annotation);
    },
    prepareForCanvas: function(annotation) {
        return scaleAnnotation(this, annotation);
    }
};
geometry.line = {
    label: 'Line',
    draw: function(ctx, line) {
        var ox = scalingFactor * line[0][0];
        var oy = scalingFactor * line[0][1];
        var mx = scalingFactor * line[1][0]; 
        var my = scalingFactor * line[1][1];
        ctx.strokeStyle = geometryColor;
        ctx.beginPath();
        ctx.moveTo(ox,oy);
        ctx.lineTo(mx,my);
        ctx.stroke();
    },
    prepareForStorage: function(annotation) {
        return unscaleAnnotation(this, annotation);
    },
    prepareForCanvas: function(annotation) {
        return scaleAnnotation(this, annotation);
    } 
};
geometry.point = {
    label: 'Point',
    draw: function(ctx, point) {
        var x = scalingFactor * point[0];
        var y = scalingFactor * point[1];
        var size = 5;
        ctx.strokeStyle = geometryColor;
        ctx.beginPath();
        ctx.moveTo(x-size,y);
        ctx.lineTo(x+size,y);
        ctx.moveTo(x,y-size);
        ctx.lineTo(x,y+size);
        ctx.stroke();
    },
    prepareForStorage: function(annotation) {
        return unscaleAnnotation(this, annotation);
    },
    prepareForCanvas: function(annotation) {
        return scaleAnnotation(this, annotation);
    } 
}
geometry.circle = {
    label: 'Circle',
    draw: function(ctx, line) {
    	// ox, oy is the foci of the circle
        var ox = scalingFactor * line[0][0];
        var oy = scalingFactor * line[0][1];
        // mx, my is the edge of the circle
        var mx = scalingFactor * line[1][0]; 
        var my = scalingFactor * line[1][1];
        //radius is the distance of the line
        var dx = mx-ox;
        var dy = my-oy;
        var radius = Math.sqrt( dx*dx + dy*dy );
        
        ctx.strokeStyle = geometryColor;
        ctx.beginPath();  
        //arc(x, y, radius, startAngle, endAngle, anticlockwise)
        /*
         * The first three parameters, x and y and radius, describe a circle, the arc drawn will be part of that circle. 
         * startAngle and endAngle are where along the circle to start and stop drawing. 
         * 	0 is east, 
         * 	Math.PI/2 is south, 
         * 	Math.PI is west, 
         *  Math.PI*3/2 is north. 
         *  
         * If anticlockwise is 1 then the direction of the arc, along with the Angles for north and south, are reversed.
         */
        ctx.arc(ox,oy,radius,0,Math.PI*2,true);
        ctx.stroke();
    },
    prepareForStorage: function(annotation) {
        return unscaleAnnotation(this, annotation);
    },
    prepareForCanvas: function(annotation) {
        return scaleAnnotation(this, annotation);
    }   
}
//
function unscaleAnnotation(tool, annotation) {
    console.log("Tool: "+tool['label']);
    console.log("Annotation (orginal): "+annotation);
    
    var precision = getZoomMathPrecision();
    var scale = getZoomScale();
    
    if( getZoomNavCoordinates() != null ){
        var dragX = getZoomNavCoordinates().x;
        var dragY = getZoomNavCoordinates().y;
        for(var item in annotation){
            for(var elem in annotation[item]){
                var offset = elem == 0 ? dragX : dragY;
                offset = -1*offset*scale;
                var coordinate = doZoomMath(annotation[item][elem],offset,precision);
                annotation[item][elem] = coordinate;
            }
        }
    }
    
    var offsetX = 0;
    var offsetY = 0;
    
    //fix zoom
    if( getZoomCoordinates() != null ){
        offsetX = getZoomCoordinates().x;
        offsetY = getZoomCoordinates().y;
    }
    
    for(var item in annotation){
        for(var elem in annotation[item]){
            var offset = elem == 0 ? offsetX : offsetY;
            annotation[item][elem] = doZoomMath(annotation[item][elem],-offset,precision) / scale;
        }
    }
    
    console.log("Fixed Annotation: "+annotation);
    return annotation;
}

function scaleAnnotation(tool, annotation) {
    //console.log("Tool: "+tool['label']);
    //console.log("Annotation: "+annotation);
    
    var precision = getZoomMathPrecision();
    var scale = getZoomScale();
    
    var offsetX = 0;
    var offsetY = 0;
    
    //fix zoom
    if( getZoomCoordinates() != null ){
        offsetX = getZoomCoordinates().x;
        offsetY = getZoomCoordinates().y;
    }
    
    for(var item in annotation){
        for(var elem in annotation[item]){
            var offset = elem == 0 ? offsetX : offsetY;
            annotation[item][elem] = doZoomMath(annotation[item][elem] * scale, offset, precision);
        }
    }
    
    if( getZoomNavCoordinates() != null ){
        var dragX = getZoomNavCoordinates().x;
        var dragY = getZoomNavCoordinates().y;
        for(var item in annotation){
            for(var elem in annotation[item]){
                var offset = elem == 0 ? dragX : dragY;
                offset = offset*scale;
                annotation[item][elem] = doZoomMath(annotation[item][elem],offset,precision);
            }
        }
    }
     
    return annotation;
}

function selectedTool(value) {
    if(value == undefined || value.length < 1) {
        return $('#workspace').data('tool');
    } else {
        clog('setting tool to '+JSON.stringify(value));
        $('#workspace').data('tool',geometry[value].tool);
    }
}
function MeasurementTool(eventHandlers) {
    this.eventHandlers = eventHandlers;
}
function isGeometryToolEnabled(cell){
    return $(cell).data('toolsDisabled') == null && hasLabel();
}

function bindMeasurementTools(selector, env) {
    // env must include the following to be passed as event.data:
    // - cell: the div containing the image and carrying annotation data
    // - canvas: the canvas
    // - ctx: a context on the canvas
    // - scaledWidth: the scaled image width
    // - scaledHeight: the scaled image height
    selector.bind('mousedown', env, function(event) {        
        var cell = event.data.cell;
        if( isGeometryToolEnabled(cell) ){
            var canvas = event.data.canvas;
            var tool = selectedTool();
            if('mousedown' in tool.eventHandlers) {
                var mx = event.pageX - canvas.offset().left;
                var my = event.pageY - canvas.offset().top;
                event.data.mx = mx;
                event.data.my = my;
                event.data.ix = (mx/scalingFactor)|0;
                event.data.iy = (mx/scalingFactor)|0;
                // call the currently selected tool
                tool.eventHandlers.mousedown(event);
            }
        }
    }).bind('mousemove', env, function(event) {
        var cell = event.data.cell;
        if( isGeometryToolEnabled(cell) ){
            var tool = selectedTool();
            var canvas = event.data.canvas;
            if('mousemove' in tool.eventHandlers) {
                var mx = mouseX(event, canvas);
                var my = mouseY(event, canvas);
                event.data.mx = mx;
                event.data.my = my;
                event.data.ix = (mx/scalingFactor)|0;
                event.data.iy = (mx/scalingFactor)|0;
                tool.eventHandlers.mousemove(event);
            }
        }
    }).bind('mouseup', env, function(event) {
        var cell = event.data.cell;
        if( isGeometryToolEnabled(cell) ){
            var tool = selectedTool();
            if('mouseup' in tool.eventHandlers) {
                tool.eventHandlers.mouseup(event);
            }
        }
    });
}
geometry.boundingBox.tool = new MeasurementTool({
    mousedown: function(event) {
        var cell = event.data.cell;
        var mx = event.data.mx;
        var my = event.data.my;
        $(cell).data('ox',mx);
        $(cell).data('oy',my);
    },
    mousemove: function(event) {
        var cell = event.data.cell;
        var ox = $(cell).data('ox');
        var oy = $(cell).data('oy');
        if(ox >= 0 && oy >= 0) {
            var ctx = event.data.ctx;
            var scaledWidth = event.data.scaledWidth;
            var scaledHeight = event.data.scaledHeight;
            var mx = event.data.mx;
            var my = event.data.my;
            var left = Math.min(ox,mx);
            var top = Math.min(oy,my);
            var w = Math.max(ox,mx) - left;
            var h = Math.max(oy,my) - top;
            /* compute a rectangle in original scale pixel space */
            var rect = [[(left/scalingFactor)|0, (top/scalingFactor)|0], [((left+w)/scalingFactor)|0, ((top+h)/scalingFactor)|0]]
            $(cell).data('boundingBox',rect);
            ctx.clearRect(0, 0, scaledWidth, scaledHeight);
            geometry.boundingBox.draw(ctx,rect);
        }
    },
    mouseup: function(event) {
        var cell = event.data.cell;
        $(cell).data('ox',-1);
        $(cell).data('oy',-1);
        //console.log($(cell).data('boundingBox'));
        var preppedBox = geometry.boundingBox.prepareForStorage($(cell).data('boundingBox'));
        //console.log(preppedBox);
        
        queueAnnotation({
            image: $(cell).data('imagePid'),
            category: categoryPidForLabel($('#label').val()),
            geometry: { boundingBox: preppedBox }
        });
        toggleSelected(cell,$('#label').val());
        
        $(document).trigger('canvasChange', [event.data.ctx.canvas, geometry.boundingBox, preppedBox]);
    }
});
// allow the user to draw a line on a cell's "new annotation" canvas
geometry.line.tool = new MeasurementTool({
    mousedown: function(event) {
        var cell = event.data.cell;
        var mx = event.data.mx;
        var my = event.data.my;
        $(cell).data('ox',mx);
        $(cell).data('oy',my);
    },
    mousemove: function(event) {
        var cell = event.data.cell;
        var ox = $(cell).data('ox');
        var oy = $(cell).data('oy');
        if(ox >= 0 && oy >= 0) {
            var ctx = event.data.ctx;
            var mx = event.data.mx;
            var my = event.data.my;
            /* compute a rectangle in original scale pixel space */
            var line = [[(ox/scalingFactor)|0, (oy/scalingFactor)|0], [(mx/scalingFactor)|0, (my/scalingFactor)|0]]
            $(cell).data('line',line);
            ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
            geometry.line.draw(ctx,line);
        }
    },
    mouseup: function(event) {
        var cell = event.data.cell;
        $(cell).data('ox',-1);
        $(cell).data('oy',-1);
        //console.log($(cell).data('line'));
        var preppedLine = geometry.line.prepareForStorage($(cell).data('line'));
        //console.log(preppedLine);
        
        queueAnnotation({
            image: $(cell).data('imagePid'),
            category: categoryPidForLabel($('#label').val()),
            geometry: { line: preppedLine }
        });
        toggleSelected(cell,$('#label').val());
        $(document).trigger('canvasChange', [event.data.ctx.canvas, geometry.line, preppedLine]);
    }
});
//allow the user to draw a line on a cell's "new annotation" canvas
geometry.point.tool = new MeasurementTool({
    mousedown: function(event) {
        var cell = event.data.cell;
        var ctx = event.data.ctx;
        var mx = event.data.mx;
        var my = event.data.my;
        /* compute a rectangle in original scale pixel space */
        var line = [(mx/scalingFactor)|0, (my/scalingFactor)|0]
        $(cell).data('point',line);
        ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
        geometry.point.draw(ctx,line);
        $(cell).data('inpoint',1);
    },
    mousemove: function(event) {
        var cell = event.data.cell;
        var point = $(cell).data('inpoint');
        if(point != undefined) {
            var ctx = event.data.ctx;
            var mx = event.data.mx;
            var my = event.data.my;
            /* compute a rectangle in original scale pixel space */
            var line = [(mx/scalingFactor)|0, (my/scalingFactor)|0]
            $(cell).data('point',line);
            ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
            geometry.point.draw(ctx,line);
        }
    },
    mouseup: function(event) {
        var cell = event.data.cell;
        //console.log($(cell).data('point'));
        var preppedPoint = geometry.point.prepareForStorage($(cell).data('point'));
        //console.log(preppedPoint);
        queueAnnotation({
            image: $(cell).data('imagePid'),
            category: categoryPidForLabel($('#label').val()),
            geometry: { point: preppedPoint }
        });
        toggleSelected(cell,$('#label').val());
        $(cell).removeData('inpoint');
        $(document).trigger('canvasChange',[event.data.ctx.canvas, geometry.point, preppedPoint]);
    }
});
//allow the user to draw a circle on a cell's "new annotation" canvas
geometry.circle.tool = new MeasurementTool({
    mousedown: function(event) {
        var cell = event.data.cell;
        var mx = event.data.mx;
        var my = event.data.my;
        $(cell).data('ox',mx);
        $(cell).data('oy',my);
    },
    mousemove: function(event) {
        var cell = event.data.cell;
        var ox = $(cell).data('ox');
        var oy = $(cell).data('oy');
        if(ox >= 0 && oy >= 0) {
            var ctx = event.data.ctx;
            var mx = event.data.mx;
            var my = event.data.my;
            /* compute a rectangle in original scale pixel space */
            var line = [[(ox/scalingFactor)|0, (oy/scalingFactor)|0], [(mx/scalingFactor)|0, (my/scalingFactor)|0]]
            $(cell).data('circle',line);
            ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
            geometry.circle.draw(ctx,line);
        }
    },
    mouseup: function(event) {
        var cell = event.data.cell;
        
        $(cell).data('ox',-1);
        $(cell).data('oy',-1);
        
        //console.log($(cell).data('circle'));
        var preppedCircle = geometry.circle.prepareForStorage($(cell).data('circle'));
        //console.log(preppedCircle);
        queueAnnotation({
            image: $(cell).data('imagePid'),
            category: categoryPidForLabel($('#label').val()),
            geometry: { circle: preppedCircle }
        });
        toggleSelected(cell,$('#label').val());
        $(document).trigger('canvasChange',[event.data.ctx.canvas, geometry.circle,preppedCircle]);
    }
});
