/*
 * ZOOM Tool 
 * Adam Shepherd 
 * adam@whoi.edu
 * 05/09/2012
 * version 0.1
 *
 */
var startScale = new Number(1);
var scaleFactor = new Number(1.1);
var is_zooming = false;

//zoom tool
var toolsPanel = '#rightPanel';
var zoomToolName = 'zoomTool';
var zoomTool = '#'+zoomToolName;
var modalSelector = 'ctrl';
//zoom tool modal button
var zoomModalButtonName = 'zoomModalButton';
var zoomModalButton = '#'+zoomModalButtonName;
var zoomMode = modalSelector+'+f'
var zoomButtonText = 'ZOOM ('+zoomMode+')';
//zoom tool reset button
var resetZoomModalButtonName = 'resetZoomModalButton';
var resetZoomMode = modalSelector+'+g';
var resetZoomButtonText = 'RESET ('+resetZoomMode+')';

//used to identify the image layer
var imgName = 'image';

var zoomEvents = {};

/**** ZOOM FUNCTIONS ****/

//detect mouse scroll => Firefox
zoomEvents['DOMMouseScroll'] = function(e){
    var scroll = e;
    while(!scroll.detail && scroll.originalEvent){
     scroll = scroll.originalEvent;
    }

    return executeScroll(scroll.detail);
}
////detect mouse scroll => IE, Opera, Safari
zoomEvents['mousewheel'] = function(e){
    return executeScroll(e.delta);
}
/**** END OF ZOOM FUNCTIONS ****/

/**** DRAG FUNCTIONS ****/
zoomEvents['mousedown'] = function(evt){
    var cell = getZoomImage();
    $(cell).data('mouseDown', true);
    
    var ox = evt.clientX;
    var oy = evt.clientY;
    
    if( getZoomNavCoordinates() != null ){
        var navX = new Number(getZoomNavCoordinates().x);
        var navY = new Number(getZoomNavCoordinates().y);
        ox = ox - navX;
        oy = oy - navY;
    }
    setZoomDragOffset(ox,oy);
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

            var startDragOffset = getZoomDragOffset();
            var moveX = evt.clientX - startDragOffset.x
            var moveY = evt.clientY - startDragOffset.y;
            navigate(moveX, moveY);

        } else {
            //clog('drag not allowed');  
            navigate(0, 0);
        }
    }
}
/**** END OF DRAG FUNCTIONS ****/



$(document).ready(function(){
    
    //setup the zoom tool in the tool panel
    $('<BR>').attr('clear','all').appendTo(toolsPanel);
    $('<BR>').attr('clear','all').appendTo(toolsPanel);
    $('<FIELDSET>').attr('id',zoomToolName).appendTo(toolsPanel);
    $('<LEGEND>').html('<span class="toolTitle">Zoom</span>').appendTo(zoomTool);

    $('<A>').attr('id', zoomModalButtonName).attr('href', '#')
            .text(zoomButtonText)
            .addClass('ui-state-default')
            .addClass('button').button()
            .click(function() {
                toggleZoomMode();
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
        toggleZoomMode(); 
    });
    
    //detect reset zoom button presses
    $(document).bind('keydown', resetZoomMode, function() {
        resetZoom();
    });
    
    //listen for image cell loading
    $(document).bind('cellLoaded', function(event, cell){ 
        setZoomScale(startScale);
        for(var evt in zoomEvents){
            getZoomImage().bind(evt, zoomEvents[evt]);
        }
        resetZoom();
    });

    //listen for canvasChange
    $(document).bind('canvasChange', function(event){
	console.log('receiving canvasChange and calling scaleAllLayers');
	scaleAllLayers();
    });
    
});

/** ZOOM MODE FUNCTIONS **/

//cursor functions
var grabHandler = function() {
    $(this).removeClass('hand').addClass('grabbing');
}
var handHandler = function() {
    $(this).removeClass('grabbing').addClass('hand');
}

//toggle zoom mode
function toggleZoomMode(){
    
    var was_zooming = is_zooming;
    is_zooming = !is_zooming;
    
    if( getZoomImageSize() != 1 ){
        is_zooming = false;
    }

    var cell = getZoomImage();
    
    if(is_zooming){
                
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
    setZoomNavCoordinates(0,0);
    setZoomDragOffset(0,0);
    console.log('resetting zoom');
    scaleAllLayers();
}

/** END OF ZOOM MODE FUNCTIONS **/


/** SCALING FUNCTIONS **/

function navigate(x,y){

    var cell = getZoomImage();
    var scale = getZoomScale();
    
    //ACTUAL IMAGE BORDER = TRANSLATE / SCALE
    var navX = $(cell).data('translatePos').x/scale;
    var navY = $(cell).data('translatePos').y/scale;

    if( Math.abs(x) >= Math.abs(navX) ){
        x = (x < 0) ? navX : -1*navX;
    }
    if( Math.abs(y) >= Math.abs(navY) ){
       y = (y < 0) ? navY : -1*navY;
    }

    setZoomNavCoordinates( x, y);
    scaleAllLayers();
}

function zoom(){
    changeZoomScale(scaleFactor);
    scaleAllLayers();
}

function shrink(){  
    
    var x;
    var y;
    if( getZoomNavCoordinates() != null ){
        x = getZoomNavCoordinates().x;
        y = getZoomNavCoordinates().y;
    }

    
    //ACTUAL IMAGE BORDER = TRANSLATE / SCALE
    var scale = getZoomScale();
    var navX = $(cell).data('translatePos').x/scale;
    var navY = $(cell).data('translatePos').y/scale;
    
    changeZoomScale(1/scaleFactor);
    if( getZoomScale() == startScale ){
       setZoomNavCoordinates( x, y);            
    }
    
    scale = getZoomScale();
    navX = $(cell).data('translatePos').x/scale;
    navY = $(cell).data('translatePos').y/scale;
    
    if( x != undefined && y != undefined ){
        if( Math.abs(x) >= Math.abs(navX) ){
            x = (x < 0) ? navX : -1*navX;
        }
        if( Math.abs(y) >= Math.abs(navY) ){
           y = (y < 0) ? navY : -1*navY;
        }
    }
    
    scaleAllLayers();
}

function scaleAllLayers(){
    console.log('entering scaleAllLayers');
    if( validateScale(getZoomScale()) ){
        
        var cell = getZoomImage();
        var width = $(cell).data('width');
        var height= $(cell).data('height');
	if(width == undefined) {
	    console.log('WARNING: width is undefined');
	}
        var scale = getZoomScale();
        var newWidth = width * scale;
        var newHeight = height * scale;

        var x = -((newWidth-width)/2);
        var y = -((newHeight-height)/2);
        $(cell).data('translatePos',{x: x, y: y});
        
        var navX = getZoomNavCoordinates().x;
        var navY = getZoomNavCoordinates().y;
        
        $.each($(cell).find('canvas'), function(index,canvas){
            var canvasID = getZoomCanvasName($(canvas).attr('id'));  
            
            var rt = new Date();
            var ctx = canvas.getContext("2d");
            var annotations = $(cell).data(canvasID);
            
            if( canvasID == 'pending' ) {
                if( annotations == undefined ){
                    annotations = [];
                }
		var imPid = $(cell).data('imagePid');
		if(imPid in pending()) {
                    $.each(pending()[imPid], function(ix, ann) {
			annotations.push(ann);
                    });
		}
            }
            
            ctx.save();
            ctx.translate(x, y);
            ctx.scale(scale, scale);
            ctx.clearRect(0, 0, width, height);
            
            if( canvasID == imgName){

                ctx.drawImage(getZoomImage().data('image'), navX, navY, width, height);

            } else if( annotations != undefined ){

                $.each(annotations, function(index, ann) { 
                    clog(canvasID+"::scale => "+ann);
                    showAnnotationGeometry(ctx,ann);
                });

            } else {
                //clog("skipping: "+canvasID);
            }

            ctx.restore();
        });
    }
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
}
function changeZoomScale(diff){
    var newScale = getZoomScale() * diff;
    if( validateScale(newScale) ){
        setZoomScale(newScale);
    }
}
function getZoomIsZooming(){
    return is_zooming;
}

function getZoomDragOffset(){
    return getZoomImage().data('startDragOffset');
}
function setZoomDragOffset(ox,oy){
    getZoomImage().data('startDragOffset', {x: ox, y: oy});
}
function getZoomNavCoordinates(){
    return getZoomImage().data('nav-coordinates');
}
function setZoomNavCoordinates(xc,yc){
    getZoomImage().data('nav-coordinates', {x: xc, y: yc});
}
function getZoomCoordinates(){
    return getZoomImage().data('translatePos');
}
function getZoomCanvasName(cid){
    return cid.substring(0,cid.indexOf('_'));
}