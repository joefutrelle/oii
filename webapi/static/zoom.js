var startScale = 1;
var scale = startScale;
var scaleFactor = 0.20;
var is_zooming = false;
var canvasStore = {};

var toolsPanel = '#rightPanel';
var zoomModalButtonName = 'zoomModalButton';
var zoomModalButton = '#'+zoomModalButtonName;
var zoomButtonText = 'ZOOM (ctrl+f)';

var imgName = 'image';
var img = '#'+imgName;

$(document).ready(function(){
    
    setupZoom();

});

function setupZoom(){
    //console.log("setting up zoom...");
    //var images = $('#images').find('div.thumbnail');
    //if( images.length() == 1 ){

        console.log("zoom enabled...");
        
        //ZOOM Modal
        $("<a>").attr("id", zoomModalButtonName).attr("href", '#')
                .text(zoomButtonText)
                .addClass('ui-state-default')
                .addClass('button').button()
                .click(function() {
                    setMode();

                })
                .mouseup(function(){
                    if($(this).is('.ui-state-active') ){
                        $(this).removeClass("ui-state-active");
                    } else {
                        $(this).addClass("ui-state-active");
                    }
                })
                .appendTo(toolsPanel);

        $(document).bind('keydown', 'ctrl+f', function() {
            setMode(); 
        });
        //end of ZOOM Modal
    /*   
    } else {
        console.log("zoom disabled...");
        $(zoomModalButton).remove();
    }
    */
}

function buildCanvasStore(){
        
    canvasStore = {};

    $(cell).data('nav-coordinates', { x: 0, y: 0});

    //detect mouse scroll
    //Firefox
     $(cell).bind('DOMMouseScroll', function(e){
         var scroll = e;
         console.log("Firefox scrolling...");
         while(!scroll.detail && scroll.originalEvent){
             scroll = scroll.originalEvent;
         }

         return executeScroll(scroll.detail);
     });

     //IE, Opera, Safari
     $(img).bind('mousewheel', function(e){
         console.log("Browser scrolling...");
         return executeScroll(e.delta);
     });
    $(cell).data('translatePos', {x: 0, y: 0});
    $(cell).data('startDragOffset', {x: 0, y: 0});
    $(cell).data('mouseDown',false);

    var canvii = $(cell).find('canvas');
    for(var c = 0; c < canvii.length; c++){
        var original = new Image();
        original.src = canvii[c].toDataURL();

        canvasStore[canvii[c].className] = {
            canvas: canvii[c],
            context: canvii[c].getContext("2d"),
            origin: original
        };
    }

    canvasStore[imgName].canvas.parentElement.addEventListener("mousedown", function(evt){
        //console.log("mousedown...");
        $(img).data('mouseDown', true);
        $(img).data('startDragOffset', {x: evt.clientX, y: evt.clientY});
    });

    canvasStore[imgName].canvas.parentElement.addEventListener("mouseup", function(evt){
        //console.log("mouseup...");
        $(img).data('mouseDown', false);
    });

    canvasStore[imgName].canvas.parentElement.addEventListener("mouseover", function(evt){
        //console.log("mouseover...");
        $(img).data('mouseDown', false);
    });

    canvasStore[imgName].canvas.parentElement.addEventListener("mouseout", function(evt){
        //console.log("mouseout...");
        $(img).data('mouseDown', false);
    });

    canvasStore[imgName].canvas.parentElement.addEventListener("mousemove", function(evt){
        if( $(img).data('mouseDown') && is_zooming ){
            //console.log("mousemove...");
            var dragging = ( scale > startScale );

            if (dragging) {

                var startDragOffset = $(img).data('startDragOffset');

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
        $(img).data('translatePos',{x: x, y: y});

    if(is_log)
        console.log('translate: '+x+','+y);

    ctx.translate(x, y);
    ctx.scale(scale, scale);

    var navX = $(img).data('nav-coordinates').x;
    var navY = $(img).data('nav-coordinates').y;

    if(is_log)
        console.log('draw at: '+navX+','+navY);

    ctx.clearRect(0, 0, width, height);
    ctx.drawImage(original, navX, navY);
    ctx.restore();
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

    $(img).data('nav-coordinates', {x: x, y: y});
    scaleAllLayers();
}

function resetZoom(){
    scale = startScale;
    $(img).data('nav-coordinates', {x: 0, y: 0});
    scaleAllLayers();
}

function zoom(){
    scale = scale + scaleFactor;
    scaleAllLayers();
}

function shrink(){
    scale = scale - scaleFactor;
    if( scale == startScale ){
       console.log("fix image draw....");
       $(img).data('nav-coordinates', {x: 0, y: 0});            
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

function validateScale(){
    var bool = scale >= startScale;
    if( !bool ) scale = startScale;
    return bool;
}

/** END OF SACLING FUNCTIONS **/

/** ZOOM MODE FUNCTIONS **/

var grabHandler = function() {
    $(this).removeClass("hand").addClass("grabbing");
}
var handHandler = function() {
    $(this).removeClass("grabbing").addClass("hand");
}

function setMode(){
    var was_zooming = is_zooming;
    
    is_zooming = !is_zooming;

    console.log("Images: "+$('#images').find('div.thumbnail').size());
    if( $('#images').find('div.thumbnail').size() != 1 ){
        is_zooming = false;
    }
    
    //console.log("ZOOMING: "+is_zooming);
    
    if(is_zooming){
        
        buildCanvasStore();
        
        $(zoomModalButton).css({'border': '2px dotted black'});
        $(img).removeClass("pointer")
                  .addClass("hand");
         //set the cursor
        $(img).bind({
          mousedown: grabHandler,
          mouseup: handHandler
        });        
    } else if(was_zooming){
        $(zoomModalButton).css({'border': ''});
        $(img).unbind('mousedown', grabHandler)
                  .unbind('mouseup',handHandler)
                  .addClass("pointer");    
        resetZoom();
    }  else {
        alert("ZOOM can't be used right now");
    }
}
/** END OF ZOOM MODE FUNCTIONS **/