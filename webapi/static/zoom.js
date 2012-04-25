/*
 * TO DO: 
 * 
 * 1) update canvas store when canvas is added/updated/deleted
 * 2) 
 *
 *
 */
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

$(document).ready(function(){
    
    $("select, input").bind('keydown', 'ctrl', function() {
        $(this).blur();
    });
    
    $(document).bind('keydown', 'ctrl+f', function() {
        console.log("about to set Zoom mode");
        setMode(); 
    });
    
    /*
    //lose focus of selects as they hinder the hotkey
    $("select, input").change(function(){
        console.log("blurring...");
        $(this).blur();
    });
    */
    
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
            
    

});

/** ZOOM MODE FUNCTIONS **/

var grabHandler = function() {
    $(this).removeClass("hand").addClass("grabbing");
}
var handHandler = function() {
    $(this).removeClass("grabbing").addClass("hand");
}

function setMode(){
    console.log("called setMode()");
    
    var was_zooming = is_zooming;
    
    is_zooming = !is_zooming;

    console.log("Images: "+getImageSize());
    
    if( getImageSize() != 1 ){
        is_zooming = false;
    }

    var cell = getImage();
    
    if(is_zooming){
        
        console.log("zooming...");
        
        buildCanvasStore();
        
        $(zoomModalButton).css({'border': '2px dotted black'});
        $(cell).removeClass("pointer").addClass("hand");
         //set the cursor
        $(cell).bind({
          mousedown: grabHandler,
          mouseup: handHandler
        });        
    } else if(was_zooming){
        
        console.log("not zooming anymore...");
        
        $(zoomModalButton).css({'border': ''});
        $(cell).unbind('mousedown', grabHandler)
               .unbind('mouseup',handHandler)
               .addClass("pointer");    
        resetZoom();
    } else {
        alert("ZOOM can't be used right now");
    }
}

function buildCanvasStore(){
    
    canvasStore = {};

    var cell = getImage();
    $(cell).data('nav-coordinates', {x: 0, y: 0});

    //detect mouse scroll
    //Firefox
     $(cell).bind('DOMMouseScroll', function(e){
         var scroll = e;
         //console.log("Firefox scrolling...");
         while(!scroll.detail && scroll.originalEvent){
             scroll = scroll.originalEvent;
         }

         return executeScroll(scroll.detail);
     });

     //IE, Opera, Safari
     $(cell).bind('mousewheel', function(e){
         //console.log("Browser scrolling...");
         return executeScroll(e.delta);
     });
     
    $(cell).data('translatePos', {x: 0, y: 0});
    $(cell).data('startDragOffset', {x: 0, y: 0});
    $(cell).data('mouseDown',false);

    var canvases = $(cell).find('canvas');
    
    if( canvases.length > 0 ){
        
        var width = $(cell).data('width');
        var height= $(cell).data('height');
        for(var c = 0; c < canvases.length; c++){

            //console.log(canvii[c]);

            var original = $("<canvas>").attr("width", width).attr("height", height)[0];
            original.getContext("2d").drawImage(canvases[c], 0, 0);

            /*
            * BUG: ***** This throws a security error when images come from different server *****
            *      http://stackoverflow.com/questions/2390232/why-does-canvas-todataurl-throw-a-security-exception
            *
            var original = new Image();
            try{
                original.src = canvii[c].toDataURL();
            }catch(err){
                console.log("Excpetion: "+err.message);
                alert("ZOOMING is not working properly for this image");
                setMode();
                return;
            }
            */
           
            var cid = $(canvases[c]).attr('id');
            canvasStore[cid.substring(0,cid.indexOf('_'))] = {
                    canvas: canvases[c],
                    context: canvases[c].getContext("2d"),
                    origin: original
            };
        }
        
        canvasStore[imgName].canvas.parentElement.addEventListener("mouseout", function(evt){
            //console.log("mouseout...");
            $(cell).data('mouseDown', false);
        });

        canvasStore[imgName].canvas.parentElement.addEventListener("mousedown", function(evt){
            //console.log("mousedown...");
            $(cell).data('mouseDown', true);
            $(cell).data('startDragOffset', {x: evt.clientX, y: evt.clientY});
        });

        canvasStore[imgName].canvas.parentElement.addEventListener("mouseup", function(evt){
            //console.log("mouseup...");
            $(cell).data('mouseDown', false);
        });

        canvasStore[imgName].canvas.parentElement.addEventListener("mouseover", function(evt){
            //console.log("mouseover...");
            $(cell).data('mouseDown', false);
        });

        canvasStore[imgName].canvas.parentElement.addEventListener("mouseout", function(evt){
            //console.log("mouseout...");
            $(cell).data('mouseDown', false);
        });

        canvasStore[imgName].canvas.parentElement.addEventListener("mousemove", function(evt){
            if( $(cell).data('mouseDown') && is_zooming ){
                //console.log("mousemove...");
                var dragging = ( scale > startScale );

                if (dragging) {

                    var startDragOffset = $(cell).data('startDragOffset');

                    var moveX = evt.clientX - startDragOffset.x
                    var moveY = evt.clientY - startDragOffset.y;
                    //console.log("move: "+moveX+","+moveY);

                    navigate(moveX, moveY);

                } else {
                    console.log("drag not allowed");    
                }
            }
        });
        
        $(cell).change(function(){
              console.log("***** thumbnail changed *****");
        });
    }
}

function resetZoom(){
    console.log("zooming...");
    scale = startScale;
    getImage().data('nav-coordinates', {x: 0, y: 0});
    scaleAllLayers();
}

/** END OF ZOOM MODE FUNCTIONS **/


/** SCALING FUNCTIONS **/

function scaleAllLayers(){
    if( validateScale() ){
        
        var cell = getImage();
        var width = $(cell).data('width');
        var height= $(cell).data('height');
        //console.log(width+":"+height);
        
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
    var cell = getImage();
    
    if(is_log){
        console.log('dimensions at: '+newWidth+','+newHeight);
    }
    
    
    ctx.save();
    
    var width = $(cell).data('width');
    var height= $(cell).data('height');
    var x = -((newWidth-width)/2);
    var y= -((newHeight-height)/2);

    if(is_image_canvas)
        $(cell).data('translatePos',{x: x, y: y});

    if(is_log)
        console.log('translate: '+x+','+y);

    ctx.translate(x, y);
    ctx.scale(scale, scale);

    var navX = $(cell).data('nav-coordinates').x;
    var navY = $(cell).data('nav-coordinates').y;

    if(is_log)
        console.log('draw at: '+navX+','+navY);

    ctx.clearRect(0, 0, width, height);
    ctx.drawImage(original, navX, navY);
    ctx.restore();
}

function navigate(x,y){

    var cell = getImage();
    var width = $(cell).data('width');
    var height= $(cell).data('height');
    
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

    getImage().data('nav-coordinates', {x: x, y: y});
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
       getImage().data('nav-coordinates', {x: 0, y: 0});            
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

/** END OF SCALING FUNCTIONS **/

/** HELPER FUNCTIONS **/

function getImage(){
    return $('#images').find('div.thumbnail:last');
}
function getImageSize(){
    return $('#images').find('div.thumbnail').size();
}