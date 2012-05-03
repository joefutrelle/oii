/*
 * 
 * 
 *
 *
 */
var debug = true;
var profile = false;

var zoomPrecision = 2;
var startScale = new Number(1);
var zoomScale = startScale;
var scaleFactor = new Number(0.1);
var is_zooming = false;
var canvasStore = {};

var toolsPanel = '#rightPanel';
var modalSelector = 'ctrl';

var zoomModalButtonName = 'zoomModalButton';
var zoomModalButton = '#'+zoomModalButtonName;
var zoomMode = modalSelector+'+f'
var zoomButtonText = 'ZOOM ('+zoomMode+')';

var resetZoomModalButtonName = 'resetZoomModalButton';
var resetZoomMode = modalSelector+'+g';
var resetZoomButtonText = 'RESET ('+resetZoomMode+')';

var imgName = 'image';

$(document).ready(function(){
    
    
    //lose focus of selects,inputs as they hinder the hotkeys
    $("select, input").bind('keydown', modalSelector, function() {
        $(this).blur();
    });
    
    $(document).bind('keydown', zoomMode, function() {
        setMode(); 
    });
    $(document).bind('keydown', resetZoomMode, function() {
        resetZoom();
    });
    
    //listen for commits
    $(document).bind('commit', function(event, message){ 
        /*
        if( is_zooming ){
            buildCanvasStore();
        }
        */
    });
    //listen for assignment changes
    $(document).bind('changeAssignment', function(event, message){ 
        zoomScale = startScale;
        resetCanvasStore();
    });

    
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
            
    $("<a>").attr("id", resetZoomModalButtonName).attr("href", '#')
            .text(resetZoomButtonText)
            .addClass('button').button()
            .click(function() {
                resetZoom();
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

var zoomEvents = {};
//detect mouse scroll
//Firefox
zoomEvents['DOMMouseScroll'] = function(e){
    var scroll = e;
    while(!scroll.detail && scroll.originalEvent){
     scroll = scroll.originalEvent;
    }

    return executeScroll(scroll.detail);
}
//IE, Opera, Safari
zoomEvents['mousewheel'] = function(e){
    return executeScroll(e.delta);
}
zoomEvents['mousedown'] = function(evt){
    var cell = getZoomImage();
    $(cell).data('mouseDown', true);
    $(cell).data('startDragOffset', {x: evt.clientX, y: evt.clientY});
}

zoomEvents['mouseup'] = function(evt){
    var cell = getZoomImage();
    $(cell).data('mouseDown', false);
}

zoomEvents['mouseover'] = function(evt){
    var cell = getZoomImage();
    $(cell).data('mouseDown', false);
}

zoomEvents['mouseout'] = function(evt){
    var cell = getZoomImage();
    $(cell).data('mouseDown', false);
}

zoomEvents['mousemove'] = function(evt){
    var cell = getZoomImage();
    if( $(cell).data('mouseDown') && is_zooming ){
        var dragging = ( zoomScale > startScale );

        if (dragging) {

            var startDragOffset = $(cell).data('startDragOffset');

            var moveX = evt.clientX - startDragOffset.x
            var moveY = evt.clientY - startDragOffset.y;
            if(debug) console.log("move: "+moveX+","+moveY);

            navigate(moveX, moveY);

        } else {
            //console.log("drag not allowed");  
            navigate(0, 0);
        }
    }
}

function setMode(){
    
    var was_zooming = is_zooming;
    is_zooming = !is_zooming;
    
    if( getZoomImageSize() != 1 ){
        is_zooming = false;
    }

    var cell = getZoomImage();
    
    if(is_zooming){
        
        console.log("zooming: "+zoomScale);
        
        $(cell).find('canvas:first').css({'border': '2px dotted black'});
        
        buildCanvasStore();
        
        $(zoomModalButton).css({'border': '2px dotted black'});
        $(cell).removeClass("pointer")
               .addClass("hand")
               .data('toolsDisabled',true);
         //set the cursor
        $(cell).bind({
          mousedown: grabHandler,
          mouseup: handHandler
        });        
    } else if(was_zooming){
        
        console.log("zooming STOPPED...");
        
        $(cell).find('canvas:first').css({'border': ''});
        
        $(zoomModalButton).css({'border': ''});
        $(cell).unbind('mousedown', grabHandler)
               .unbind('mouseup',handHandler)
               .addClass("pointer")
               .removeData('toolsDisabled');    
        //resetZoom();
    } else {
        alert("ZOOM can't be used right now");
    }
}

function buildCanvasStore(){
    var time = new Date();
    resetCanvasStore();

    var cell = getZoomImage();
    $(cell).data('nav-coordinates', {x: 0, y: 0});
    $(cell).data('translatePos', {x: 0, y: 0});
    $(cell).data('startDragOffset', {x: 0, y: 0});
    $(cell).data('mouseDown',false);

    var canvases = $(cell).find('canvas');
    
    if( canvases.length > 0 ){
        
        var width = $(cell).data('width');
        var height= $(cell).data('height');
        for(var c = 0; c < canvases.length; c++){
            //var time = new Date();
            var original;
            //console.log(canvii[c]);
            var cid = $(canvases[c]).attr('id');
            var storeName = cid.substring(0,cid.indexOf('_'));
            if( imgName == storeName ){
                original = getZoomImage().data('image');
            } else {
                original = $("<canvas>").attr("width", width).attr("height", height)[0];
                original.getContext("2d").drawImage(canvases[c], 0, 0);
            }

            canvasStore[storeName] = {
                    canvas: canvases[c],
                    context: canvases[c].getContext("2d"),
                    origin: original
            };
            if(profile) console.log(storeName+": "+(new Date()-time));
        }

        for(var evt in zoomEvents){
            var exists = false;
            for(var event in $(cell).data('events')[evt]){
                if( zoomEvents[evt] == $(cell).data('events')[evt][event]['handler'] ){
                    exists = true;
                    break;
                }
            }
            if( !exists ){
                $(cell).bind(evt, zoomEvents[evt]);
            }
        }
    }
    if( profile ) console.log("build canvas store: "+(new Date()-time));
}

function resetZoom(){
    zoomScale = startScale;
    getZoomImage().data('nav-coordinates', {x: 0, y: 0});
    scaleAllLayers();
}

/** END OF ZOOM MODE FUNCTIONS **/


/** SCALING FUNCTIONS **/

function scaleAllLayers(){
    var time = new Date();
    if( validateScale() ){
        
        var cell = getZoomImage();
        var width = $(cell).data('width');
        var height= $(cell).data('height');
        //console.log(width+":"+height);
        
        var newWidth = width * zoomScale;
        var newHeight = height * zoomScale;

        var image_debug = debug;
        
        for(var canvas in canvasStore) {
            var rt = new Date();
            redraw(canvasStore[canvas].context, newWidth, newHeight, canvasStore[canvas].origin, canvas, image_debug);
            if( profile ) console.log("TOTAL["+canvas+"]: "+(new Date()-rt));
            image_debug = false;
        }
    }
    if( profile ) console.log("zoom time: "+(new Date()-time));
}

function redraw(ctx, newWidth, newHeight, original, canvasID, log_debug){
    
    var time = new Date();
    var is_image_canvas = true; //canvasStore['image'].context == ctx;
    var cell = getZoomImage();
    
    if(log_debug){
        //console.log('dimensions at: '+newWidth+','+newHeight);
    }
    
    ctx.save();
    if(profile){
        console.log("save["+canvasID+"]: "+(new Date()-time));
        time = new Date();
    }
    
    var width = $(cell).data('width');
    var height= $(cell).data('height');
    var x = -((newWidth-width)/2);
    var y= -((newHeight-height)/2);

    if(is_image_canvas){
        $(cell).data('translatePos',{x: x, y: y});
    }
    
    if(log_debug){
        //console.log('translate: '+x+','+y);
    }
    
    ctx.translate(x, y);
    if(profile){
        console.log("translate["+canvasID+"]: "+(new Date()-time));
        time = new Date();
    }
    ctx.scale(zoomScale, zoomScale);
    if(profile){
        console.log("scale["+canvasID+"]: "+(new Date()-time));
        time = new Date();
    }
    ctx.clearRect(0, 0, width, height);
    if(profile){
        console.log("clear["+canvasID+"]: "+(new Date()-time));
        time = new Date();
    }
    
    var navX = $(cell).data('nav-coordinates').x;
    var navY = $(cell).data('nav-coordinates').y;

    if(log_debug){
        console.log('draw at: '+navX+','+navY);
    }

    if( canvasID == imgName){
        ctx.drawImage(original, navX, navY, width, height);
    } else {
        ctx.drawImage(original, navX, navY);
    }
    
    ctx.restore();
    if(profile) console.log("draw and restore["+canvasID+"]: "+(new Date()-time));
}

function navigate(x,y){

    var cell = getZoomImage();

    if(debug){
        console.log('proposed nav: '+x+','+y);
    }
    
    //ACTUAL IMAGE BORDER = TRANSLATE / SCALE
    var navX = getZoomNumber(($(cell).data('translatePos').x/zoomScale),0);
    var navY = getZoomNumber(($(cell).data('translatePos').y/zoomScale),0);
    if(debug) console.log("border: "+navX+","+navY);

    if( Math.abs(x) >= Math.abs(navX) ){
        x = (x < 0) ? navX : -1*navX;
        console.log("DANGER X: "+navX);
    }
    if( Math.abs(y) >= Math.abs(navY) ){
       y = (y < 0) ? navY : -1*navY;
       console.log("DANGER Y: "+navY);
    }

    if(debug) console.log('fixed nav: '+x+','+y);

    getZoomImage().data('nav-coordinates', {x: x, y: y});
    scaleAllLayers();
}

function zoom(){
    setZoomScale(scaleFactor);
    scaleAllLayers();
}

function shrink(){    
    setZoomScale(-scaleFactor);
    if( zoomScale == startScale ){
       getZoomImage().data('nav-coordinates', {x: 0, y: 0});            
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
        if(debug) console.log("zooming: "+zoomScale);
    }
    //make sure the page doesn't scroll
    return !is_zooming;
}

function validateScale(){
    var bool = zoomScale >= startScale;
    if( !bool ) zoomScale = startScale;
    return bool;
}

function resetCanvasStore(){
    canvasStore = {};
}

/** END OF SCALING FUNCTIONS **/

/** HELPER FUNCTIONS **/

function getZoomImage(){
    return $('#images').find('div.thumbnail:last');
}
function getZoomImageSize(){
    return $('#images').find('div.thumbnail').size();
}
function getZoomScale(){
    return zoomScale;
}
function setZoomScale(diff){
    zoomScale = doZoomMath(zoomScale,diff,getZoomMathPrecision());
    console.log("set scale to: "+zoomScale+" vs. "+doZoomMath(zoomScale,diff,getZoomMathPrecision()));
}
function getZoomIsZooming(){
    return is_zooming;
}
function getZoomNavCoordinates(){
    return getZoomImage().data('nav-coordinates');
}
function getZoomCoordinates(){
    return getZoomImage().data('translatePos');
}
function doZoomMath(a,b,p){
    if( p == undefined ) p = getZoomPrecision();
    if(debug) console.log("Add "+b+" to "+a+" with precision: "+p);
    var num = getZoomNumber( (parseFloat(a)+parseFloat(b)) , p );
    console.log(num+" vs. "+(parseFloat(a)+parseFloat(b)));
    return num;
}
function getZoomNumber(n,p){
    if( p == undefined ) p = getZoomMathPrecision();
    return parseFloat(n).toFixed(p);
}
function getZoomMathPrecision(){
    return zoomPrecision;
}