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
    var scroll = e;
    while(!scroll.detail && scroll.originalEvent){
     scroll = scroll.originalEvent;
    }
    if('delta' in scroll) { // IE, Opera, Safari
	return executeScroll(scroll.delta);
    } else if('wheelDeltaY' in scroll) { // chrome
	return executeScroll(0-scroll.wheelDeltaY);
    }
}
/**** END OF ZOOM FUNCTIONS ****/

/**** DRAG FUNCTIONS ****/
zoomEvents['mousedown'] = function(evt){
    var cell = getZoomImage();
    $(cell).data('mouseDown', true);

    var ox = evt.clientX;
    var oy = evt.clientY;

    setZoomDragOffset(ox,oy);
}

zoomEvents['mouseup'] = function(evt){
    var cell = getZoomImage();
    $(cell).data('mouseDown', false);
    //setZoomDragOffset(0,0);
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
            console.log('Drag to: '+evt.clientX+','+evt.clientY);
            console.log('drag offset: '+startDragOffset.x+','+startDragOffset.y);

            var zs = getZoomScale();
            var moveX = evt.clientX - startDragOffset.x;
            var moveY = evt.clientY - startDragOffset.y

            console.log('drag moved: '+moveX,moveY);
            setZoomDragOffset(new Number(startDragOffset.x) + moveX, new Number(startDragOffset.y) + moveY);
            console.log('scale: '+zs);
            //scale the drag
            moveX = moveX/zs;
            moveY = moveY/zs;
            console.log('images moved(scaled): '+moveX+','+moveY);
            if( getZoomNavCoordinates() != null ){
                var navX = new Number(getZoomNavCoordinates().x);
                var navY = new Number(getZoomNavCoordinates().y);
                console.log('viewfinder at: '+navX+','+navY);
                moveX += navX;
                moveY += navY;
            }

            console.log('set viewfinder to: '+moveX+','+moveY);

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
    var navX = getTranslatePos().x/scale;
    var navY = getTranslatePos().y/scale;

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
    changeZoomScale(1/scaleFactor);
    scaleAllLayers();
}

function scaleAllLayers(){
    console.log('entering scaleAllLayers');
        
        var cell = getZoomImage();
        var width = $(cell).data('width');
        var height= $(cell).data('height');
	if(width == undefined) {
	    console.log('WARNING: width is undefined');
	}
        var scale = getZoomScale();
    if(scale < startScale) {
	resetZoom();
	if(is_zooming) {
	    toggleZoomMode();
	}
	return;
    }
        var newWidth = width * scale;
        var newHeight = height * scale;

        var x = -((newWidth-width)/2);
        var y = -((newHeight-height)/2);
	setTranslatePos(x,y);
        
        var navX = getZoomNavCoordinates().x;
        var navY = getZoomNavCoordinates().y;
        
        $.each($(cell).find('canvas'), function(index,canvas){
            var canvasID = getZoomCanvasName($(canvas).attr('id'));  
            
            var rt = new Date();
            var ctx = canvas.getContext("2d");
            
            ctx.save();
            ctx.translate(x, y);
            ctx.scale(scale, scale);
            ctx.clearRect(0, 0, width, height);

            
            if( canvasID == imgName){

                ctx.drawImage(getZoomImage().data('image'), navX, navY, width, height);

            } else {
	    var annotations = [];
	    if($('#workspace').data('showExisting') && canvasID == 'existing') {
		$.each($(cell).data(canvasID), function(ix,ann) {
                    showAnnotationGeometry(ctx,ann,EXISTING_COLOR);
		});
		annotations = $(cell).data(canvasID);
	    }
            
            if( canvasID == 'pending' ) {
                if( annotations == undefined ){
                    annotations = [];
                }
		var imPid = $(cell).data('imagePid');
		if(imPid in pending()) {
                    $.each(pending()[imPid], function(ix, ann) {
			showAnnotationGeometry(ctx,ann,PENDING_COLOR);
                    });
		}
            }

		if(annotations != undefined) {
                $.each(annotations, function(index, ann) { 
                    showAnnotationGeometry(ctx,ann);
                });
		}

            }

            ctx.restore();
        });
}


function executeScroll(direction){
    console.log('executing scroll, direction = '+direction);
    if(direction < 0 && !is_zooming) {
	toggleZoomMode();
    }
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
    return s;
}
function changeZoomScale(diff) {
    var newScale = getZoomScale() * diff;
    setZoomScale(newScale);
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
function setTranslatePos(xc,yc) {
    getZoomImage().data('translatePos',{x:xc,y:yc});
}
function getTranslatePos(){
    return getZoomImage().data('translatePos');
}
function getZoomCanvasName(cid){
    return cid.substring(0,cid.indexOf('_'));
}
// coordinate systems, dimensions and transformations used:
// image space: the coordinate system of the full-sized image in pixels
// canvas space: the coordinate system of the displayed canvas, which is scaled by startScale
// startScale: default scale of the interface; the scale at which the image exactly fits the canvas.
// zoomScale: the zoomed-in scale. when==startScale, not zoomed. when > startScale, zoomed in. when < startScale, zoomed out.
// scaleFactor: how much to change the scale factor by when zooming in or out.
// translatePos: ?
// zoomNavCoordinates: ?
// zoomDragOffset: ?



