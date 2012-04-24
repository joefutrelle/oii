var startScale = 1;
var scale = startScale;
var scaleFactor = 0.20;

var is_zooming = false;

var canvasStore = {};
var layerCount = 0;
var img = new Image();
img.src = 'http://localhost:5000/static/images/zoom/test.jpg';

var width = img.width; //600;
var height = img.height; //600;

var navEdge = 100;
var navFactor = 27;

var controls = $("#controls");
controls.css({'margin-top': '-20px'});

$(document).ready(function(){

    $("#cell").width(width);
    $("#cell").height(height);
    $("#cell").css({'border':'1px solid blue'});
    $("#cell").addClass("pointer");
    $("#cell").data('nav-coordinates', { x: 0, y: 0});

    addLayer($("#cell"),'image', width, height);
    //addLayer($("#cell"), 'circle', width, height);
    addLayer($("#cell"), 'line', width, height);
    addLayer($("#cell"), 'line2', width, height);
    addLayer($("#cell"), 'line3', width, height);

    //detect mouse scroll
    //Firefox
     $('#cell').bind('DOMMouseScroll', function(e){
         var scroll = e;
         console.log("Firefox scrolling...");
         while(!scroll.detail && scroll.originalEvent){
             scroll = scroll.originalEvent;
         }

         return executeScroll(scroll.detail);
     });

     //IE, Opera, Safari
     $('#cell').bind('mousewheel', function(e){
         console.log("Browser scrolling...");
         return executeScroll(e.delta);
     });

    $('#zoom').click(function() {
        setMode();

    }).css({'padding':'5px'});

    $('#reset').click(function() {
        scale = startScale;
        $("#cell").data('nav-coordinates', {x: 0, y: 0});
        scaleAllLayers();

    }).css({'padding':'5px'});

});

/** PAGE INIT FUNCTIONS **/
function addLayer(parent, name, cWidth, cHeight){
    var id = '#'+name;
    var className = name+'-canvas';
    var canvas = $("<canvas>")
                    .attr("id", id)
                    .attr("width", cWidth)
                    .attr("height", cHeight)
                    .addClass(className)
                    .css({ position: 'absolute',
                      'z-index': layerCount,
                      left: '1',
                      top: '1'})
                    .appendTo("#cell");
        
    canvasStore[name] = {
        canvas: canvas[0],
        context: canvas[0].getContext("2d")
    };

    layerCount++;

    drawLayer(name);

    if( name == 'image' ){

        $('#cell').data('translatePos', {x: 0, y: 0});
        $('#cell').data('startDragOffset', {x: 0, y: 0});
        $('#cell').data('mouseDown',false);
                
        canvasStore[name].canvas.parentElement.addEventListener("mousedown", function(evt){
            //console.log("mousedown...");
            $('#cell').data('mouseDown', true);
            $('#cell').data('startDragOffset', {x: evt.clientX, y: evt.clientY});
        });

        canvasStore[name].canvas.parentElement.addEventListener("mouseup", function(evt){
            //console.log("mouseup...");
            $('#cell').data('mouseDown', false);
        });

        canvasStore[name].canvas.parentElement.addEventListener("mouseover", function(evt){
            //console.log("mouseover...");
            $('#cell').data('mouseDown', false);
        });

        canvasStore[name].canvas.parentElement.addEventListener("mouseout", function(evt){
            //console.log("mouseout...");
            $('#cell').data('mouseDown', false);
        });

        canvasStore[name].canvas.parentElement.addEventListener("mousemove", function(evt){
            if( $('#cell').data('mouseDown') && is_zooming ){
                //console.log("mousemove...");
                var dragging = ( scale > startScale );

                if (dragging) {

                    var startDragOffset = $('#cell').data('startDragOffset');

                    var moveX = evt.clientX - startDragOffset.x
                    var moveY = evt.clientY - startDragOffset.y;
                    //console.log("move: "+moveX+","+moveY);

                    navigate(moveX, moveY);

                } else {
                    console.log("drag not allowed");    
                }
            }
        });   
    }
    
    //store the default canvas data in its orginal scale
    var origin = $("<canvas>").attr("width", width).attr("height", height)[0];
    origin.getContext("2d").drawImage(canvasStore[name].canvas, 0, 0);
    canvasStore[name].origin = origin;
}

function drawLayer(type) {
    if( 'image' == type ) {
        buildImage(canvasStore[type].context, img);
    } else if( 'circle' == type ) {
        buildCircle(canvasStore[type].context, width, height);
    } else if( 'line' == type ) {
        var start = width * .4;
        var end = width * .6;
        buildLine(canvasStore[type].context, start, start, end, end, '#f00');
    } else if( 'line2' == type ) {
        var startX = width * .6;
        var startY = width * .4;
        var endX = width * .4;
        var endY = width * .6;
        buildLine(canvasStore[type].context, startX, startY, endX, endY, '#00f');
    } else if( 'line3' == type ) {
        var startX = width * .5;
        var startY = width * .65;
        var endX = width * .5;
        var endY = width * .35;
        buildLine(canvasStore[type].context, startX, startY, endX, endY, '#0f0');
    }

}
/** END OF PAGE INIT FUNCTIONS **/

/** SCALING FUNCTIONS **/
function scaleAllLayers(){
    if( validateScale() ){
        var newWidth = width * scale;
        var newHeight = height * scale;

        for(var canvas in canvasStore) {
            redraw(canvasStore[canvas].context, newWidth, newHeight, canvasStore[canvas].origin);
        }
    }
}

function zoom(){
    scale = scale + scaleFactor;
    scaleAllLayers();
}

function shrink(){
    scale = scale - scaleFactor;
    if( scale == startScale ){
       console.log("fix image draw....");
       $("#cell").data('nav-coordinates', {x: 0, y: 0});            
    }
    scaleAllLayers();
}

function executeScroll(direction){
    if( is_zooming ){
        if(direction > 0){
            shrink();
        } else {
            zoom();
        }
    }
    //make sure the page doesn't scroll
    return !is_zooming;
}

function navigate(x,y){

    /*
    console.log('proposed nav: '+x+','+y);
    console.log("width: "+width+", height: "+height);
    console.log("scaled: "+(width*scale)+","+(height*scale));
    */
    var numberofScales = (scale-startScale)/scaleFactor;
    //console.log("# of scales: "+numberofScales);
    //console.log("# of scales * scale: "+(numberofScales*scaleFactor));

    var navX =(((width * scale)-width)/2);
    var navY =(((height * scale)-height)/2);
    //console.log("border? "+navX+","+navY);

    navX=navX-navX*(numberofScales*scaleFactor);
    navY=navY-navY*(numberofScales*scaleFactor);
    console.log("revised border? "+navX+"("+navX*(numberofScales*scale)+"),"+navY+"("+navY*(numberofScales*scale)+")");

    if( Math.abs(x) > Math.abs(navX) ){
        x = (x < 0) ? -1*navX : navX;
    }
    if( Math.abs(y) > Math.abs(navY) ){
        y = (y < 0) ? -1*navY : navY;
    }

    console.log('fixed nav: '+x+','+y);

    $("#cell").data('nav-coordinates', {x: x, y: y});
    scaleAllLayers();

}

/** END OF SCALING FUNCTIONS **/

/** HELPER FUNCTIONS **/
function redraw(ctx, newWidth, newHeight, original){

    var is_image_canvas = true; //canvasStore['image'].context == ctx;
    var is_log = is_image_canvas && false;

    if(is_log){
        console.log('dimensions at: '+newWidth+','+newHeight);

    }
    ctx.save();
    var x = -((newWidth-width)/2);
    var y= -((newHeight-height)/2);

    if(is_image_canvas)
        $('#image').data('translatePos',{x: x, y: y});

    if(is_log)
        console.log('translate: '+x+','+y);

    ctx.translate(x, y);
    ctx.scale(scale, scale);

    var navX = $("#cell").data('nav-coordinates').x;
    var navY = $("#cell").data('nav-coordinates').y;

    if(is_log)
        console.log('draw at: '+navX+','+navY);

    ctx.clearRect(0, 0, width, height);
    ctx.drawImage(original, navX, navY);
    ctx.restore();
}

function validateScale(){
    var bool = scale >= startScale;
    if( !bool ) scale = startScale;
    return bool;
}

function buildImage(ctx, img){
    ctx.drawImage(img,0,0);
}

function buildCircle(ctx, width, height){
    var radius = width/8;
    ctx.arc(width/2, height/2, radius, 0, Math.PI*2, true);
    ctx.fill();
}

function buildLine(ctx, startX, startY, endX, endY, style){
    ctx.strokeStyle = style;
    ctx.beginPath();
    ctx.moveTo(startX,startY);
    ctx.lineTo(endX,endY);
    ctx.stroke();
}
/** END OF HELPER FUNCTIONS **/



//
$(document).bind('keydown', 'ctrl+f', function() {
    setMode(); 
});

var grabHandler = function() {
    $(this).removeClass("hand").addClass("grabbing");
}
var handHandler = function() {
    $(this).removeClass("grabbing").addClass("hand");
}

function setMode(){
    is_zooming = !is_zooming;

    //console.log("ZOOMING: "+is_zooming);
    
    if(is_zooming){
        $('#zoom').css({'border': '2px dotted black'});
        $("#cell").removeClass("pointer")
                  .addClass("hand");
         //set the cursor
        $("#cell").bind({
          mousedown: grabHandler,
          mouseup: handHandler
        });        
    } else {
        $('#zoom').css({'border': ''});
        $("#cell").unbind('mousedown', grabHandler)
                  .unbind('mouseup',handHandler)
                  .addClass("pointer");    
    }  
}