/*
 * ZOOM Tool 
 * Adam Shepherd 
 * adam@whoi.edu
 * 05/09/2012
 * version 0.1
 *
 */
var debug = false;
var profile = false;

var startScale = new Number(1);

var scaleFactor = new Number(0.1);
var is_zooming = false;

var toolsPanel = '#rightPanel';
var modalSelector = 'ctrl';

var zoomToolName = 'zoomTool';
var zoomTool = '#'+zoomToolName;

var zoomModalButtonName = 'zoomModalButton';
var zoomModalButton = '#'+zoomModalButtonName;
var zoomMode = modalSelector+'+f'
var zoomButtonText = 'ZOOM ('+zoomMode+')';

var resetZoomModalButtonName = 'resetZoomModalButton';
var resetZoomMode = modalSelector+'+g';
var resetZoomButtonText = 'RESET ('+resetZoomMode+')';

var imgName = 'image';

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
        var dragging = ( getZoomScale() > startScale );

        if (dragging) {

            var startDragOffset = $(cell).data('startDragOffset');

            var moveX = evt.clientX - startDragOffset.x
            var moveY = evt.clientY - startDragOffset.y;
            if(debug) console.log('move: '+moveX+','+moveY);

            navigate(moveX, moveY);

        } else {
            //console.log('drag not allowed');  
            navigate(0, 0);
        }
    }
}



$(document).ready(function(){
    
    $('<BR>').attr('clear','all').appendTo(toolsPanel);
    $('<BR>').attr('clear','all').appendTo(toolsPanel);
    $('<FIELDSET>').attr('id',zoomToolName).appendTo(toolsPanel);
    $('<LEGEND>').html('<span class="toolTitle">Zoom</span>').appendTo(zoomTool);

    $('<A>').attr('id', zoomModalButtonName).attr('href', '#')
            .text(zoomButtonText)
            .addClass('ui-state-default')
            .addClass('button').button()
            .click(function() {
                setMode();
            })
            .mouseup(function(){
                if($(this).is('.ui-state-active') ){
                    $(this).removeClass('ui-state-active');
                } else {
                    $(this).addClass('ui-state-active');
                }
            })
            .appendTo(zoomTool);
            
    $('<A>').attr('id', resetZoomModalButtonName).attr('href', '#')
            .text(resetZoomButtonText)
            .addClass('button').button()
            .click(function() {
                resetZoom();
            })
            .appendTo(zoomTool);
            
    
    //lose focus of selects,inputs as they hinder the hotkeys
    $('select, input').bind('keydown', modalSelector, function() {
        $(this).blur();
    });
    
    //detect zoom button presses
    $(document).bind('keydown', zoomMode, function() {
        setMode(); 
    });
    //detect reset zoom button presses
    $(document).bind('keydown', resetZoomMode, function() {
        resetZoom();
    });
    
    //listen for image cell loading
    $(document).bind('cellLoaded', function(event, cell){ 
        console.log("******** cell ["+cell+"] loaded ***********");
        setZoomScale(startScale);
        for(var evt in zoomEvents){
            console.log(evt+":"+zoomEvents[evt]);
            getZoomImage().bind(evt, zoomEvents[evt]);
        }
        resetZoom();
    });

    //listen for canvasChange
    $(document).bind('canvasChange', function(event){
       scaleAllLayers();
    });
    
});

/** ZOOM MODE FUNCTIONS **/

var grabHandler = function() {
    $(this).removeClass('hand').addClass('grabbing');
}
var handHandler = function() {
    $(this).removeClass('grabbing').addClass('hand');
}

function setMode(){
    
    var was_zooming = is_zooming;
    is_zooming = !is_zooming;
    
    if( getZoomImageSize() != 1 ){
        is_zooming = false;
    }

    var cell = getZoomImage();
    
    if(is_zooming){
        
        if(debug) console.log('zooming: '+getZoomScale());
        
        $(zoomModalButton).css({'border': '2px dotted black'});
        $(cell).removeClass('pointer')
               .addClass('hand')
               .data('toolsDisabled',true);
         //set the cursor
        $(cell).bind({
          mousedown: grabHandler,
          mouseup: handHandler
        });        
    } else if(was_zooming){
        
        if(debug) console.log('zooming STOPPED...');
                
        $(zoomModalButton).css({'border': ''});
        $(cell).unbind('mousedown', grabHandler)
               .unbind('mouseup',handHandler)
               .addClass('pointer')
               .removeData('toolsDisabled');    
    } else {
        alert('ZOOM cannot be used right now');
    }
}

function resetZoom(){
    setZoomScale(startScale);
    getZoomImage().data('nav-coordinates', {x: 0, y: 0});
    scaleAllLayers();
}

/** END OF ZOOM MODE FUNCTIONS **/


/** SCALING FUNCTIONS **/

function scaleAllLayers(){
    var time = new Date();
    if( validateScale(getZoomScale()) ){
        
        var cell = getZoomImage();
        var width = $(cell).data('width');
        var height= $(cell).data('height');
        var scale = getZoomScale();
        var newWidth = width * scale;
        var newHeight = height * scale;

        var x = -((newWidth-width)/2);
        var y = -((newHeight-height)/2);
        $(cell).data('translatePos',{x: x, y: y});
        
        var navX = $(cell).data('nav-coordinates').x;
        var navY = $(cell).data('nav-coordinates').y;
        
        $.each($(cell).find('canvas'), function(index,canvas){
            var canvasID = getZoomCanvasName($(canvas).attr('id'));  
            
            var rt = new Date();
            var ctx = canvas.getContext("2d");
            var annotations = $('#workspace').data(canvasID);
            
            ctx.save();
            ctx.translate(x, y);
            ctx.scale(scale, scale);
            ctx.clearRect(0, 0, width, height);
            
            if( canvasID == imgName){

                ctx.drawImage(getZoomImage().data('image'), navX, navY, width, height);

            } else if( annotations != undefined ){

                console.log(" redrawing "+canvasID+" annotations: "+annotations);
                $.each(annotations, function(index, ann) { 
                    showAnnotationGeometry(ctx,ann);
                });

            } else {
                console.log("skipping: "+canvasID);
            }

            ctx.restore();

            if( profile ) console.log('TOTAL['+canvas+']: '+(new Date()-rt));
        });
    }
    if( profile ) console.log('zoom time: '+(new Date()-time));
}

function navigate(x,y){

    var cell = getZoomImage();
    var scale = getZoomScale();
    
    if(debug){
        console.log('proposed nav: '+x+','+y);
    }
    
    //ACTUAL IMAGE BORDER = TRANSLATE / SCALE
    var navX = $(cell).data('translatePos').x/scale;
    var navY = $(cell).data('translatePos').y/scale;
    if(debug) console.log('border: '+navX+','+navY);

    if( Math.abs(x) >= Math.abs(navX) ){
        x = (x < 0) ? navX : -1*navX;
        if(debug) console.log('DANGER X: '+navX);
    }
    if( Math.abs(y) >= Math.abs(navY) ){
       y = (y < 0) ? navY : -1*navY;
       if(debug) console.log('DANGER Y: '+navY);
    }

    if(debug) console.log('fixed nav: '+x+','+y);

    getZoomImage().data('nav-coordinates', {x: x, y: y});
    scaleAllLayers();
}

function zoom(){
    changeZoomScale(scaleFactor);
    scaleAllLayers();
}

function shrink(){    
    changeZoomScale(-scaleFactor);
    if( getZoomScale() == startScale ){
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
        //if(debug) 
            console.log('zooming: '+getZoomScale());
    }
    //make sure the page doesn't scroll
    return !is_zooming;
}

function validateScale(newScale){
    var bool = newScale >= startScale;
    if( !bool ) scale = startScale;
    return bool;
}

/** END OF SCALING FUNCTIONS **/




/** HELPER FUNCTIONS **/

function getZoomImage(){
    return getImageCanvii();
}
function getZoomImageSize(){
    return $('#images').find('div.thumbnail').size();
}
function getZoomScale(){
    var scale = $('#workspace').data('zoomScale');
    if( scale != null && scale != undefined ) return scale;
    scale = startScale;
    setZoomScale(scale);
    return scale;
}
function setZoomScale(s){
    $('#workspace').data('zoomScale', s);
    console.log("scale set to: "+s);
}
function changeZoomScale(diff){
    var newScale = getZoomScale()+diff;
    if( validateScale(newScale) ){
        setZoomScale(newScale);
    }
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
function getZoomCanvasName(cid){
    return cid.substring(0,cid.indexOf('_'));
}