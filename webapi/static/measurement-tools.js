function MeasurementTool(eventHandlers) {
    this.eventHandlers = eventHandlers;
    this.name = 'Unnamed measurement tool';
}
MeasurementTool.prototype.bindTo = function(selector, env) {
    // env must include the following to be passed as event.data:
    // - cell: the div containing the image and carrying annotation data
    // - ctx: the canvas context for the "new annotation" canvas $(cell).find('canvas.new')
    // - iw: the scaled image width
    // - ih: the scaled image height
    env.tool = this;
    selector.bind('mousedown', env, function(event) {
        var cell = event.data.cell;
        if('mousedown' in event.data.tool.eventHandlers) {
            var mx = event.pageX - $(this).offset().left;
            var my = event.pageY - $(this).offset().top;
            event.data.mx = mx;
            event.data.my = my;
            event.data.ix = (mx/scalingFactor)|0;
            event.data.iy = (mx/scalingFactor)|0;
            event.data.tool.eventHandlers.mousedown(event);
        }
    }).bind('mousemove', env, function(event) {
        if('mousemove' in event.data.tool.eventHandlers) {
            var mx = event.pageX - $(this).offset().left;
            var my = event.pageY - $(this).offset().top;
            event.data.mx = mx;
            event.data.my = my;
            event.data.ix = (mx/scalingFactor)|0;
            event.data.iy = (mx/scalingFactor)|0;
            event.data.tool.eventHandlers.mousemove(event);
        }
    }).bind('mouseup', env, function(event) {
        if('mouseup' in event.data.tool.eventHandlers) {
            event.data.tool.eventHandlers.mouseup(event);
        }
    });
}
//allow the user to draw a bounding box on a cell's "new annotation" canvas
var boundingBoxTool = new MeasurementTool({
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
            var iw = event.data.iw;
            var ih = event.data.ih;
            var mx = event.data.mx;
            var my = event.data.my;
            ctx.clearRect(0,0,iw,ih);
            ctx.strokeStyle = geometryColor;
            var left = Math.min(ox,mx);
            var top = Math.min(oy,my);
            var w = Math.max(ox,mx) - left;
            var h = Math.max(oy,my) - top;
            /* compute a rectangle in original scale pixel space */
            var rect = [[(left/scalingFactor)|0, (top/scalingFactor)|0], [((left+w)/scalingFactor)|0, ((top+h)/scalingFactor)|0]]
            $(cell).data('boundingBox',rect);
            ctx.strokeRect(left, top, w, h);
        }
    },
    mouseup: function(event) {
        var cell = event.data.cell;
        $(cell).data('ox',-1);
        $(cell).data('oy',-1);
        queueAnnotation({
            image: $(cell).data('image_pid'),
            category: categoryPidForLabel($('#label').val()),
            geometry: { boundingBox: $(cell).data('boundingBox') }
        });
        toggleSelected(cell,$('#label').val());
    }
});
// allow the user to draw a line on a cell's "new annotation" canvas
var lineTool = new MeasurementTool({
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
            ctx.clearRect(0,0,event.data.iw,event.data.ih);
            ctx.strokeStyle = geometryColor;
            /* compute a rectangle in original scale pixel space */
            var line = [[(ox/scalingFactor)|0, (oy/scalingFactor)|0], [(mx/scalingFactor)|0, (my/scalingFactor)|0]]
            $(cell).data('line',line);
            ctx.beginPath();
            ctx.moveTo(ox,oy);
            ctx.lineTo(mx,my);
            ctx.stroke();
        }
    },
    mouseup: function(event) {
        var cell = event.data.cell;
        $(cell).data('ox',-1);
        $(cell).data('oy',-1);
        queueAnnotation({
            image: $(cell).data('image_pid'),
            category: categoryPidForLabel($('#label').val()),
            geometry: { line: $(cell).data('line') }
        });
        toggleSelected(cell,$('#label').val());
    }
});
