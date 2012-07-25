  // globals (FIXME: make preferences)
var scalingFactor = 0.75;
var poly_simplifyTolerance = 3;
// assumes PENDING_COLOR is set globally (FIXME make preference)
// geometric tool support
var geometry = {};
geometry.boundingBox = {
    label: 'Bounding box',
    draw: function(ctx, boundingBox, color) {
        var left = scalingFactor * boundingBox[0][0];
        var top = scalingFactor * boundingBox[0][1];
        var right = scalingFactor * boundingBox[1][0]; 
        var bottom = scalingFactor * boundingBox[1][1];
        ctx.strokeStyle = color;
	//clog('bounding box color is '+color);
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
    draw: function(ctx, line, color) {
        var ox = scalingFactor * line[0][0];
        var oy = scalingFactor * line[0][1];
        var mx = scalingFactor * line[1][0]; 
        var my = scalingFactor * line[1][1];
	//clog('line color is '+color);
        ctx.strokeStyle = color;
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
geometry.path = {
    label: 'Path',
    draw: function(ctx, line, color) {
        var oy = scalingFactor * line[0][1];
        ctx.strokeStyle = color;
	//clog('path color is '+color);
        ctx.beginPath();
	$.each(line, function(ix, pt) {
	    var px = scalingFactor * pt[0];
	    var py = scalingFactor * pt[1];
	    if(ix == 0) {
		ctx.moveTo(px, py);
	    } else {
		ctx.lineTo(px, py);
	    }
	});
        ctx.stroke();
    },
    prepareForStorage: function(annotation) {
        return unscaleAnnotation(this, annotation);
    },
    prepareForCanvas: function(annotation) {
        return scaleAnnotation(this, annotation);
    } 
};
geometry.closedPath = {
    label: 'Closed path',
    draw: geometry.path.draw,
    prepareForStorage: function(annotation) {
        return unscaleAnnotation(this, annotation);
    },
    prepareForCanvas: function(annotation) {
        return scaleAnnotation(this, annotation);
    } 
};
geometry.polyline = { 
    label: 'Polyline',
    draw: geometry.path.draw,
    prepareForStorage: function(annotation) {
        return unscaleAnnotation(this, annotation);
    },
    prepareForCanvas: function(annotation) {
        return scaleAnnotation(this, annotation);
    } 
};
geometry.closedPolyline = { 
    label: 'Closed polyline',
    draw: geometry.path.draw,
    prepareForStorage: function(annotation) {
        return unscaleAnnotation(this, annotation);
    },
    prepareForCanvas: function(annotation) {
        return scaleAnnotation(this, annotation);
    } 
};
geometry.point = {
    label: 'Point',
    draw: function(ctx, point, color) {
        var x = scalingFactor * point[0][0];
        var y = scalingFactor * point[0][1];
        var size = 5;
	//clog('point stroke color ='+color);
        ctx.strokeStyle = color;
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
    draw: function(ctx, line, color) {
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
        
	//clog('circle stroke color ='+color);
        ctx.strokeStyle = color;
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

    var scale = getGeometryScale();
    
    //set in zoom
    var navCoordinates = getImageCanvii().data('nav-coordinates');

    console.log('checking nav coords');
    if( navCoordinates != undefined ){
        var dragX = navCoordinates.x / scalingFactor;
        var dragY = navCoordinates.y / scalingFactor;
        for(var item in annotation){
            for(var elem in annotation[item]){
                var offset = elem == 0 ? dragX : dragY;
                offset = -1*offset*scale;
                var coordinate = annotation[item][elem]+offset;
                annotation[item][elem] = coordinate;
            }
        }
    }
    
    var offsetX = 0;
    var offsetY = 0;

    //fix zoom
    var translate = getImageCanvii().data('translatePos');
    if( translate != undefined ){
        offsetX = translate.x / scalingFactor;
        offsetY = translate.y / scalingFactor;
    }

    console.log('annotation is currently ' + annotation);
    for(var item in annotation){
        for(var elem in annotation[item]){
	    console.log('correcting annotation.' + item);
            var offset = elem == 0 ? offsetX : offsetY;
            annotation[item][elem] = (annotation[item][elem]-offset) / scale;
        }
    }
    
    console.log('fixed annotation is ' + annotation);
    return annotation;
}

function scaleAnnotation(tool, annotation) {
    //console.log('Tool: '+tool['label']);
    //console.log('Annotation: '+annotation);

    var fixedAnnotation = $.extend(true, {}, annotation);
    var navCoordinates = getImageCanvii().data('nav-coordinates');
    if( navCoordinates != null ){
        var dragX = navCoordinates.x / scalingFactor;
        var dragY = navCoordinates.y / scalingFactor;
        //console.log("Drag: "+dragX+","+dragY);
        for(var item in annotation) {
            for(var elem in annotation[item]){
                var offset = elem == 0 ? dragX : dragY;
                fixedAnnotation[item][elem] = doGeometryMath(fixedAnnotation[item][elem],offset);
            }
        }
    }
    
    //console.log('Fixed Annotation: '+JSON.stringify(fixedAnnotation));
    return fixedAnnotation;
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
                event.data.ix = (mx/scalingFactor);
                event.data.iy = (mx/scalingFactor);
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
                event.data.ix = (mx/scalingFactor);
                event.data.iy = (mx/scalingFactor);
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
            var rect = [[(left/scalingFactor), (top/scalingFactor)], [((left+w)/scalingFactor), ((top+h)/scalingFactor)]]
            $(cell).data('boundingBox',rect);
            ctx.clearRect(0, 0, scaledWidth, scaledHeight);
            geometry.boundingBox.draw(ctx,rect,PENDING_COLOR);
        }
    },
    mouseup: function(event) {
        var cell = event.data.cell;
        $(cell).data('ox',-1);
        $(cell).data('oy',-1);
        //console.log($(cell).data('boundingBox'));
        var preppedBox = geometry.boundingBox.prepareForStorage($(cell).data('boundingBox'));
        //console.log(preppedBox);
        
        queueAnnotation(cell, { boundingBox: preppedBox });
        select(cell,$('#label').val());
    }
});
// allow the user to draw a line on a cell's 'new annotation' canvas
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
            var line = [[(ox/scalingFactor), (oy/scalingFactor)], [(mx/scalingFactor), (my/scalingFactor)]]
            $(cell).data('line',line);
            ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
            geometry.line.draw(ctx,line,PENDING_COLOR);
        }
    },
    mouseup: function(event) {
        var cell = event.data.cell;
        $(cell).data('ox',-1);
        $(cell).data('oy',-1);
        console.log('pre-prepped line: '+$(cell).data('line'));
        var preppedLine = geometry.line.prepareForStorage($(cell).data('line'));
        console.log('post-prepped line: '+preppedLine);
        
        queueAnnotation(cell, { line: preppedLine });
        select(cell,$('#label').val());
    }
});
geometry.polyline.tool = new MeasurementTool({
    mousedown: function(event) {
        var cell = event.data.cell;
        var mx = event.data.mx;
        var my = event.data.my;
        var px = $(cell).data('px');//previous x,y; the point we're currently rubberbanding from
        var py = $(cell).data('py');
	console.log('px='+px+', py='+py);
	if(px==mx && py==my) { // doubleclick: commit
            $(cell).data('px',-1);
            $(cell).data('py',-1);
	    var line = $(cell).data('polyline');
	    console.log('doubleclickclick while rubberbanding, line = '+JSON.stringify(line));
            console.log('pre-prepped line: '+line);
            var preppedLine = geometry.polyline.prepareForStorage(line);
            console.log('post-prepped line: '+preppedLine);
            queueAnnotation(cell, { polyline: preppedLine });
            select(cell,$('#label').val());
        } else if(px >= 0 && py >= 0) { // click while rubberbanding: put down a point
            var ctx = event.data.ctx;
            var mx = event.data.mx;
            var my = event.data.my;
            var line = $(cell).data('polyline');
	    line.push([mx/scalingFactor, my/scalingFactor]);
	    $(cell).data('polyline',line);
	    console.log('click while rubberbanding, line = '+JSON.stringify(line));
            ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
            geometry.polyline.draw(ctx,line,PENDING_COLOR); // draw the existing line
	    $(cell).data('px',mx);
	    $(cell).data('py',my);
	} else { // start line
            $(cell).data('px',mx);//previous x,y; the point we're currently rubberbanding from
            $(cell).data('py',my);
	    $(cell).data('polyline',[[mx/scalingFactor, my/scalingFactor]]);
	    console.log('click when not rubberbanding, line = '+JSON.stringify($(cell).data('polyline')));
	    // no need to draw yet
	}
    },
    mousemove: function(event) {
        var cell = event.data.cell;
        var px = $(cell).data('px');//previous x,y; the point we're currently rubberbanding from
        var py = $(cell).data('py');
        if(px >= 0 && py >= 0) {
            var ctx = event.data.ctx;
            var mx = event.data.mx;
            var my = event.data.my;
            var line = $(cell).data('polyline');
            ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
            geometry.polyline.draw(ctx,line,PENDING_COLOR); // draw the existing line
	    ctx.lineTo(mx, my); // now draw the rubberbanded current addition
	    ctx.stroke();
        }
    },
    mouseup: function(event) {
	// do nothing
    }
});
geometry.closedPolyline.tool = new MeasurementTool({
    mousedown: function(event) {
        var cell = event.data.cell;
        var mx = event.data.mx;
        var my = event.data.my;
        var px = $(cell).data('px');//previous x,y; the point we're currently rubberbanding from
        var py = $(cell).data('py');
	console.log('px='+px+', py='+py);
	if(px==mx && py==my) { // doubleclick: commit
            $(cell).data('px',-1);
            $(cell).data('py',-1);
	    var line = $(cell).data('polyline');
	    line.push([line[0][0], line[0][1]]);
	    console.log('doubleclickclick while rubberbanding, line = '+JSON.stringify(line));
            console.log('pre-prepped line: '+line);
            var preppedLine = geometry.polyline.prepareForStorage(line);
            console.log('post-prepped line: '+preppedLine);
            queueAnnotation(cell, { polyline: preppedLine });
            select(cell,$('#label').val());
        } else if(px >= 0 && py >= 0) { // click while rubberbanding: put down a point
            var ctx = event.data.ctx;
            var mx = event.data.mx;
            var my = event.data.my;
            var line = $(cell).data('polyline');
	    line.push([mx/scalingFactor, my/scalingFactor]);
	    $(cell).data('polyline',line);
	    console.log('click while rubberbanding, line = '+JSON.stringify(line));
            ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
            geometry.polyline.draw(ctx,line,PENDING_COLOR); // draw the existing line
	    $(cell).data('px',mx);
	    $(cell).data('py',my);
	} else { // start line
            $(cell).data('px',mx);//previous x,y; the point we're currently rubberbanding from
            $(cell).data('py',my);
	    $(cell).data('polyline',[[mx/scalingFactor, my/scalingFactor]]);
	    console.log('click when not rubberbanding, line = '+JSON.stringify($(cell).data('polyline')));
	    // no need to draw yet
	}
    },
    mousemove: function(event) {
        var cell = event.data.cell;
        var px = $(cell).data('px');//previous x,y; the point we're currently rubberbanding from
        var py = $(cell).data('py');
        if(px >= 0 && py >= 0) {
            var ctx = event.data.ctx;
            var mx = event.data.mx;
            var my = event.data.my;
            var line = $(cell).data('polyline');
            ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
            geometry.polyline.draw(ctx,line,PENDING_COLOR); // draw the existing line
	    ctx.lineTo(mx, my); // now draw the rubberbanded current addition
	    ctx.stroke();
        }
    },
    mouseup: function(event) {
    }
});
// allow the user to draw a freeform line on a cell's 'new annotation' canvas
geometry.path.tool = new MeasurementTool({
    mousedown: function(event) {
        var cell = event.data.cell;
        var mx = event.data.mx;
        var my = event.data.my;
        $(cell).data('ox',mx);
        $(cell).data('oy',my);
	var path = [[mx/scalingFactor, my/scalingFactor]];
	$(cell).data('path',path);
    },
    mousemove: function(event) {
        var cell = event.data.cell;
        var ox = $(cell).data('ox');
        var oy = $(cell).data('oy');
        if(ox >= 0 && oy >= 0) {
            var ctx = event.data.ctx;
            var mx = event.data.mx;
            var my = event.data.my;
	    var path = $(cell).data('path');
	    path.push([mx/scalingFactor, my/scalingFactor]);
	    $(cell).data('path',path);
            ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
            geometry.path.draw(ctx,path,PENDING_COLOR);
        }
    },
    mouseup: function(event) {
        var cell = event.data.cell;
	var ctx = event.data.ctx;
        $(cell).data('ox',-1);
        $(cell).data('oy',-1);
	var complexPath = $(cell).data('path');
	// use poly_simplify
	var simplePath = poly_simplify(complexPath, poly_simplifyTolerance);
        ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
        geometry.path.draw(ctx,simplePath,PENDING_COLOR);
        var preppedPath = geometry.path.prepareForStorage(simplePath);
        queueAnnotation(cell, { path: preppedPath });
        select(cell,$('#label').val());
    }
});
// closed path tool
geometry.closedPath.tool = new MeasurementTool({
    mousedown: function(event) {
        var cell = event.data.cell;
        var mx = event.data.mx;
        var my = event.data.my;
        $(cell).data('ox',mx);
        $(cell).data('oy',my);
	var path = [[mx/scalingFactor, my/scalingFactor]];
	$(cell).data('path',path);
    },
    mousemove: function(event) {
        var cell = event.data.cell;
        var ox = $(cell).data('ox');
        var oy = $(cell).data('oy');
        if(ox >= 0 && oy >= 0) {
            var ctx = event.data.ctx;
            var mx = event.data.mx;
            var my = event.data.my;
	    var path = $(cell).data('path');
	    path.push([mx/scalingFactor, my/scalingFactor]);
	    $(cell).data('path',path);
            ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
            geometry.path.draw(ctx,path,PENDING_COLOR);
        }
    },
    mouseup: function(event) {
        var cell = event.data.cell;
	var ctx = event.data.ctx;
        $(cell).data('ox',-1);
        $(cell).data('oy',-1);
	var complexPath = $(cell).data('path');
	complexPath.push([complexPath[0][0], complexPath[0][1]]);
	// use poly_simplify
	var simplePath = poly_simplify(complexPath, poly_simplifyTolerance);
        ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
        geometry.path.draw(ctx,simplePath,PENDING_COLOR);
        var preppedPath = geometry.path.prepareForStorage(simplePath);
        queueAnnotation(cell, { path: preppedPath });
        select(cell,$('#label').val());
    }
});
//allow the user to draw a line on a cell's 'new annotation' canvas
geometry.point.tool = new MeasurementTool({
    mousedown: function(event) {
        var cell = event.data.cell;
        var ctx = event.data.ctx;
        var mx = event.data.mx;
        var my = event.data.my;
        /* compute a rectangle in original scale pixel space */
        var line = [[(mx/scalingFactor), (my/scalingFactor)]];
        $(cell).data('point',line);
        ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
        geometry.point.draw(ctx,line,PENDING_COLOR);
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
            var line = [[(mx/scalingFactor), (my/scalingFactor)]];
            $(cell).data('point',line);
            ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
            geometry.point.draw(ctx,line,PENDING_COLOR);
        }
    },
    mouseup: function(event) {
        var cell = event.data.cell;
        //console.log($(cell).data('point'));
        var preppedPoint = geometry.point.prepareForStorage($(cell).data('point'));
        //console.log(preppedPoint);
        queueAnnotation(cell, { point: preppedPoint });
        select(cell,$('#label').val());
        $(cell).removeData('inpoint');
    }
});
//allow the user to draw a circle on a cell's 'new annotation' canvas
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
            var line = [[(ox/scalingFactor), (oy/scalingFactor)], [(mx/scalingFactor), (my/scalingFactor)]];
            $(cell).data('circle',line);
            ctx.clearRect(0,0,event.data.scaledWidth,event.data.scaledHeight);
            geometry.circle.draw(ctx,line,PENDING_COLOR);
        }
    },
    mouseup: function(event) {
        var cell = event.data.cell;
        
        $(cell).data('ox',-1);
        $(cell).data('oy',-1);
        
        //console.log($(cell).data('circle'));
        var preppedCircle = geometry.circle.prepareForStorage($(cell).data('circle'));
        //console.log(preppedCircle);
        queueAnnotation(cell, { circle: preppedCircle });
        select(cell,$('#label').val());
    }
});

function getGeometryScale(){
    console.log('looking for the zoomScale');
    var scale = $('#workspace').data('zoomScale');
    if( scale == null || scale == undefined ){ // FIXME null??
        scale = new Number(1);
        $('#workspace').data('zoomScale', scale);
    } 
    return scale;
}

function doGeometryMath(a,b){
    return (parseFloat(a)+parseFloat(b));
}