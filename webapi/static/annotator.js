var TARGET_SCOPE=1;
var IMAGE_SCOPE=2;
var DOMINANT_SUBSTRATE_SCOPE=3;
var SUBDOMINANT_SUBSTRATE_SCOPE=4
var PENDING_COLOR='#0f0'
var EXISTING_COLOR='#f00'
function getWorkspace(key) {
    return $('#workspace').data(key);
}
function setWorkspace(key,value) {
    $('#workspace').data(key, value);
}
// add an image to the page
// - cell: the div to draw it in
// - imageUrl: the url of the image to draw
// - scale: the scaling factor (default 1.0)
// - zoomScale: the zoom factor (independent of scaling factor, default scaling factor)
// - zoomCenter: the center of the zoom in non-scaled coordinates (if zoomed, default center of image)
function addImage(cell,imageUrl,scale,zoomScale,zoomCenter) {
    // handle defaults that we can handle
    if(scale == undefined) { scale = 1.0; }
    // populate its data
    $(cell).data('imageUrl',imageUrl);
    $(cell).data('scale',scale);
    $(cell).data('zoomScale',zoomScale);
    $(cell).data('zoomCenter',zoomCenter);
    // load the image to get geometry, and create layers
    $(cell).prepend('<img style="display:none" src="'+imageUrl+'">')
        .find('img')
        .bind('load', { cell: cell, scale: scale }, function (event) {
            var cell = event.data.cell;
            var scale = event.data.scale;
            var width = $(this).width();
            var height = $(this).height();
            var scaledWidth = width * scale;
            var scaledHeight = height * scale;
            $(cell).width(scaledWidth);
            $(cell).data('width',scaledWidth);
            $(cell).data('height',scaledHeight);
            $(cell).data('scaledWidth',scaledWidth);
            $(cell).data('scaledHeight',scaledHeight);
            $(cell).data('image',this);
	    //
            $(document).trigger('cellLoaded', cell);
	    //
	    var translate = getImageCanvii().data('translatePos');
	    if( translate != undefined ){
		console.log('translate is ['+translate.x+', '+translate.y+']');
		offsetX = translate.x;
		offsetY = translate.y;
	    }

            // create layers for
            // - the image
            // - the existing annotations
            // - the pending annotations
            // - the new annotations (during geometry selection, prior to pending)
            addImageLayer(cell,'image',imageUrl);
            addImageLayer(cell,'existing',imageUrl);
            addImageLayer(cell,'pending',imageUrl);
            addImageLayer(cell,'new',imageUrl);
            // now:
            // - display the zoomed image
            // - display the zoomed existing annotations
            // - fetch the existing annotations and display them zoomed
	    $(document).trigger('canvasChange');
            getExistingAnnotations(cell, function() {
		$(document).trigger('canvasChange');
	    });
            
            // adjust layout
            $(cell).find('div.spacer').height(scaledHeight+10);
            // bind measurement tools
            var newCanvas = getImageLayer(cell,'new');
            var ctx = getImageLayerContext(cell,'new');
            var env = { cell: cell, canvas: newCanvas, ctx: ctx, scaledWidth: scaledWidth, scaledHeight: scaledHeight }
            bindMeasurementTools(cell, env);
        });
}
function addImageLayer(cell,claz,imageUrl) {
    var scaledWidth = $(cell).data('scaledWidth');
    var scaledHeight = $(cell).data('scaledHeight');
    clog('adding canvas '+scaledWidth+','+scaledHeight);
    $(cell).append('<canvas id="'+claz+'_'+imageUrl+'" width="'+scaledWidth+'px" height="'+scaledHeight+'px" class="'+claz+' atorigin"></canvas>');
}
function getImageLayer(cell,claz) {
    return $(cell).find('canvas.'+claz);
}
function getImageLayerContext(cell,claz) {
    return getImageLayer(cell,claz)[0].getContext('2d');
}
function clearImageLayer(cell,claz) {
    var ctx = getImageLayerContext(cell,'existing');
    ctx.clearRect(0,0,$(cell).data('scaledWidth'),$(cell).data('scaledHeight'));
}
function drawImage(cell) {
    var ctx = getImageLayerContext(cell,'image')
    ctx.drawImage($(cell).data('image'),0,0,$(cell).data('scaledWidth'),$(cell).data('scaledHeight'));
}
function getExistingAnnotations(cell, callback) {
    $.get('/list_annotations/image/' + $(cell).data('imagePid'), function(r) {
        clearImageLayer(cell,'existing');
        var ctx = getImageLayerContext(cell,'existing');
        var counter = 0;
        clog("about to draw existing annotations...");
	$(cell).data('existing',[]);
        $(r).each(function(ix,ann) {
            existing(cell)[counter++] = ann;
        });
	callback();
    });
}
//cell - div with image in it
//ann - annotation
function showAnnotationGeometry(ctx,ann,color) {
    // use the appropriate drawing method to draw any geometry found    
    if('geometry' in ann) {
        var g = ann.geometry;
        for(key in ann.geometry) { // this probably should not be a loop
            var g = ann.geometry[key];
            if(g != undefined) {
                var sa = geometry[key].prepareForCanvas(ann.geometry[key]);
                geometry[key].draw(ctx, sa, color);
            }
        }
    }
}
function addCell(imagePid) {
    return $('#images').append('<div class="thumbnail"><div class="spacer"></div><div class="caption ui-widget">&nbsp;</div><div class="subcaption ui-widget"></div></div>')
        .find('div.thumbnail:last')
        .data('imagePid',imagePid)
        .data('existing',{})
        .disableSelection();
        //.trigger('cellLoaded', this);
}
function gotoPage(page,size) {
    if(page < 1) page = 1;
    clog('going to page '+page);
    clearPage();
    var offset = (page-1) * size;
    var limit = size;
    var assignment = getWorkspace('assignment');
    if(assignment == undefined) {
	clog('no assignment currently selected; changing page will have no effect');
	return;
    }
    var assignment_pid = assignment.pid;
    // FIXME include status flag after offset, incorporate upcoming fixes to GUI and #1445
    $.getJSON('/list_images/limit/'+limit+'/offset/'+offset+'/assignment/'+assignment_pid, function(r) {
	$('#offset').val(offset);
        $.each(r, function(i,entry) {
            // append image with approprite URL
            var imageUrl = entry.image;
            var imagePid = entry.pid; // for now, pid = url
            // each cell has the following data associated with it:
            // imagePid: the pid of the image
            // width: unscaled width of image
            // height: unscaled height of image
            // scaledWidth: scaled width of image
            // scaledHeight: scaled height of image
            // ox: x origin of (new, not existing) bounding box
            // oy: y origin of (new, not existing) bounding box
            // rect: the bounding box rectangle (in *non-scaled* pixel coordinates)
            clog('adding cell for '+imagePid);
            cell = addCell(imagePid);
            clog('adding image for '+imageUrl);
            addImage(cell,imageUrl,scalingFactor);
	    $("#quickImagename").html(imagePid);
	    if($('#workspace').data('login') != undefined) {
		$.getJSON('/set_status/image/'+encodeURIComponent(imagePid)+'/status/in+progress/assignment/'+assignment_pid, function(r) {
		    clog('status changed to in progress for '+imagePid);
		});
	    }
        }); // loop over images
    });
    $("#quickOffset").html(offset);
}
function clearPage() {
    $('#images').empty();
}
function setLabel(cell,label) {
    /* first convert undefined to '' */
    var previousLabel = $(cell).data('previous-label');
    previousLabel = previousLabel == undefined ? '' : previousLabel;
    $(cell).data('previous-label',previousLabel);
    /* now swap */
    $(cell).data('previous-label',$(cell).data('label'));
    $(cell).data('label',label);
    var p = $(cell).data('previous-label');
    clog('setting caption to '+label);
    $(cell).find('div.caption').html(label);
}
function unsetLabel(cell) {  /* cell = thumbnail div containing image */
    setLabel(cell,$(cell).data('previous-label'));
}
function select(cell,label) {  /* cell = thumbnail div containing image */
    /* select */
    if(label == '') { // if there's no class selected, clear everything
        $(cell).removeClass('selected');
        clearBoundingBox(cell);
    } else {
        setLabel(cell,label);
        $(cell).addClass('selected');
    }
}
function clearBoundingBox(cell) {
    var w = $(cell).data('scaledWidth');
    var h = $(cell).data('scaledHeight');
    $(cell).data('ox',-1);
    $(cell).data('oy',-1);
    var ctx = $(cell).find('canvas.new')[0].getContext('2d');
    ctx.clearRect(0,0,w,h);
}
function deselect(cell) {  /* cell = thumbnail div containing image */
    /* deselect */
    unsetLabel(cell);
    $(cell).removeClass('selected');
    clearBoundingBox(cell);
}
function toggleSelected(cell,label) { /* cell = thumbnail div containing image */
    if($(cell).hasClass('selected')) {
        deselect(cell);
    } else {
        select(cell,label);
    }
}
function commitCell(cell) {
    $(cell).removeClass('selected');
    clearBoundingBox(cell);
}
function pending() {
    return $('#workspace').data('pending');
}
function existing(cell) {
    return $(cell).data('existing');
}
function generateIds(annotations, callback) {
   /* generate an ID for each annotation */
    var n = 0;
    $.each(annotations, function(imagePid, ps) {
	$.each(ps, function(ix, p) {
	    n++;
	});
    });
    var i = n-1;
    /* FIXME hardcoded namespace */
    $.getJSON('/generate_ids/'+n+'/http://foobar.ns/ann_', function(r) {
        $.each(annotations, function(imagePid, ps) {
	    $.each(ps, function(ix, p) {
		annotations[imagePid][ix].pid = r[i--];
	    });
        });
	callback();
    });
}
function preCommit() {
    generateIds(pending(), commit);
}
function queueAnnotation(cell, geometry) {
    var ann = {
        image: $(cell).data('imagePid'),
        category: categoryPidForLabel($('#label').val()),
        geometry: geometry,
	scope: TARGET_SCOPE,
	annotator: 'http://people.net/joeblow',
	timestamp: iso8601(new Date()),
	assignment: $('#workspace').data('assignment').pid
    };
    pushAnnotation(ann);
}
function queueSubstrateAnnotation(categories, scope) {
    if(scope==DOMINANT_SUBSTRATE_SCOPE) {
	qsa(categories,scope,'dominantSubstrate');
    } else if(scope==SUBDOMINANT_SUBSTRATE_SCOPE) {
	qsa(categories,scope,'subdominantSubstrate');
    } else if(scope==IMAGE_SCOPE) {
	qsa(categories,scope,'imageNotes');
    }
}
function qsa(categories, scope, dataKey) {
    // FIXME implement
    // FIXME deal with fact that there can be more than one image per page
    $('#workspace').data(dataKey, {});
    // FIXME for now queue the substrate ann for all images on the page
    $('div.thumbnail').each(function(i,cell) {
	var imagePid = $(cell).data('imagePid');
	$.each(categories, function(j,cat) {
	    var ann = {
		image: imagePid,
		category: cat.pid,
		geometry: {},
		annotator: 'http://foobar',
		scope: scope,
		timestamp: iso8601(new Date()),
		assignment: $('#workspace').data('assignment').pid
	    };
	    HOL.add($('#workspace').data(dataKey), imagePid, ann);
	});
    });
}
function commitSubstrate(continuation) {
    var as = [];
    var gi = {};
    $.each($('#workspace').data('dominantSubstrate'), function(imagePid, anns) {
	$.each(anns, function(ix, ann) {
	    HOL.add(gi, imagePid, ann);
            as.push(ann);
            clog(ann.image+' is has dominant substrate '+ann.category+' at '+ann.timestamp+', ann_id='+ann.pid);
	});
    });
    $.each($('#workspace').data('subdominantSubstrate'), function(imagePid, anns) {
	$.each(anns, function(ix, ann) {
	    HOL.add(gi, imagePid, ann);
            as.push(ann);
            clog(ann.image+' is has subdominant substrate '+ann.category+' at '+ann.timestamp+', ann_id='+ann.pid);
	});
    });
    $.each($('#workspace').data('imageNotes'), function(imagePid, anns) {
	$.each(anns, function(ix, ann) {
	    HOL.add(gi, imagePid, ann);
            as.push(ann);
            clog(ann.image+' is has imagenotes '+ann.category+' at '+ann.timestamp+', ann_id='+ann.pid);
	});
    });
    clog('there are '+as.length+' substrate annotations');
    if(as.length > 0) {
	generateIds(gi, function() {
	    $.ajax({
		url: '/create_annotations',
		type: 'POST',
		contentType: 'json',
		dataType: 'json',
		data: JSON.stringify(as),
		success: function() {
		    continuation();
		},
		statusCode: {
		    401: function() {
			alert('please login');
		    }
		}
	    });
	});
    } else {
	continuation();
    }
}
function preCommitSubstrate() {
    // FIXME do this in one transaction
    generateIds($('#workspace').data('dominantSubstrate'),function() {
	generateIds($('#workspace').data('subdominantSubstrate'),function() {
	    generateIds($('#workspace').data('imageNotes'),function() {
		commitSubstrate();
	    });
	});
    });
}
function pushAnnotation(ann)  {
    clog('enqueing '+JSON.stringify(ann));
    HOL.add(pending(), ann.image, ann);
    $(document).trigger('canvasChange');
    $('#workspace').data('undo').push(ann.image);
}
function undo() {
    var imagePid = $('#workspace').data('undo').pop();
    if(imagePid != undefined) {
	HOL.pop(pending(), imagePid);
	$(document).trigger('canvasChange');
    }
}
function commit() {
    var as = [];
    $.each(pending(), function(imagePid, anns) {
	$.each(anns, function(ix, ann) {
            as.push(ann);
            clog(ann.image+' is a '+ann.category+' at '+ann.timestamp+', ann_id='+ann.pid);
	});
    });
    $.ajax({
        url: '/create_annotations',
        type: 'POST',
        contentType: 'json',
        dataType: 'json',
        data: JSON.stringify(as),
        success: function() {
	    resetPending();
            $('div.thumbnail.selected').each(function(ix,cell) {
                commitCell(cell);
		getExistingAnnotations(cell, function() {
		    $(document).trigger('canvasChange');
		});
            });
        },
	statusCode: {
	    401: function() {
		alert('please login');
	    }
	}
    });
}
function findNewImage(callback) {
    var ass_pid = getWorkspace('assignment').pid;
    var find_status = "new";

	//very bad hardcoding but eventually the find status might need to be part of the assignment 
        // (for this hack to work in the assignment all 283 and 284 images start as status "in progress"
	if( ass_pid == "http://habcam-data.whoi.edu/data/283" || ass_pid == "http://habcam-data.whoi.edu/data/284" ){
	   find_status = "in progress";
	} else {
	   find_status = "new";
	}

clog('user is on assignment '+ass_pid + ' find status: ' + find_status);

    $.getJSON('/find_image/offset/'+page+'/status/'+find_status+'/assignment/'+ass_pid, function(r) {
	var newPage = r.offset;
	callback(newPage);
    });
}
function deselectAll() {
    $('#workspace').data('pending',{});
    $('div.thumbnail.selected').each(function(ix,cell) {
        toggleSelected(cell);
    });
    $(document).trigger('canvasChange');
}
function listAssignments() {
    $('#assignment').append('<option value="">Select an Assignment</option>')
    $.getJSON('/list_assignments', function(r) {
        $.each(r.assignments, function(i,a) {
            $('#assignment').append('<option value="'+a.pid+'">'+elide(a.label)+'</option>')
        });
    });
}
function changeAssignment(ass_pid) {
    $('#label').val('');
    var ass_pid = $('#assignment').val();
    clog('user selected assignment '+ass_pid);
    if( ass_pid.length > 0 ){
        clog("clearing exisitng annotation store...");
        $.getJSON('/fetch_assignment/'+ass_pid, function(r) {
            clog('fetched assignment '+ass_pid);
            $('#workspace').data('assignment',r);
            $('#workspace').data('image_list',r.images);
            $.getJSON('/list_categories/'+r.mode, function(c) {
                clog('fetched categories for mode '+r.mode);
                $('#workspace').data('categories',c);
                gotoPage(1,1); // FIXME keep track of page size globally
            });
        });
    }
}
function categoryPidForLabel(label) {
    var cats = $('#workspace').data('categories');
    if(cats == undefined) { return; }
    for(var i = 0; i < cats.length; i++) {
        if(cats[i].label==label) {
            return cats[i].pid;
        }
    }
}
function categoryLabelForPid(pid) {
    var cats = $('#workspace').data('categories');
    if(cats == undefined) { return; }
    for(var i = 0; i < cats.length; i++) {
        if(cats[i].pid==pid) {
            return cats[i].label;
        }
    }
}
function resizeAll() {
    // resize the right panel
    var rp = $('#rightPanel');
    if(rp.is(':visible')) {
        rp.height($(window).height() - ((rp.outerHeight() - rp.height()) + (rp.offset().top * 2)));
    }
}

function hasLabel(){
    return $('#label').val() != null && $('#label').val().length > 0;
}

function getImageCanvii(){
    return $('#images').find('div.thumbnail:last');
}
function getCanvasForName(canvasName){
    return getImageLayer(getImageCanvii(),canvasName)[0];
}
function toggleExisting() {
    var e = $('#workspace').data('showExisting');
    if(e) {
	e = 0;
    } else {
	e = 1;
    }
    $('#workspace').data('showExisting',e);
    $(document).trigger('canvasChange');
}
function resetPending() {
    $('#workspace').data('pending',{}); // pending annotations by pid
    $('#workspace').data('undo',[]); // stack of imagePids indicating the order in which anns were queued
}
function resetImageLevelPending() {
    $('#workspace').data('dominantSubstrate',{}); // pending substrate annotations by pid
    $('#workspace').data('subdominantSubstrate',{}); // pending substrate annotations by pid
    $('#workspace').data('imageNotes',{});
}
$(document).ready(function() {
    page = 1;
    size = 1;
    resetPending();
    resetImageLevelPending();
    $('#workspace').data('showExisting',1); // whether to display existing annotations
    // inputs are ui widget styled
    $('input').addClass('ui-widget');
    // images div is not text-selectable
    $('#images').disableSelection(); // note that this is a jQuery UI function
    // images are not draggable
    $('img').live('mousedown',function(event) {
        event.preventDefault();
    });
    $('a.button').button();
    $('#prev').click(function() {
        page--;
        if(page < 1) page = 1;
        gotoPage(page,size);
    });
    $('#offset').change(function() {
	page = parseInt($('#offset').val())+1;
	gotoPage(page,size);
    });
    $('#next').click(function() {
	page++;
	gotoPage(page,size);
    });
    $('#nextNew').click(function() {
	commitSubstrate(function() {
	    findNewImage(function(pp) {
		page = pp;
		gotoPage(page,size);
	    });
	});
    });
    $('#commit').click(function() {
        preCommit();
    });
    $('#cancel').click(function() {
        deselectAll();
    });
    $('#undo').click(function() {
        undo();
    });
    $('#toggleExisting').click(function() {
	toggleExisting();
    });
    $(document).bind('keydown', 'ctrl+z', undo);
    $('#assignment').change(function() {
        changeAssignment($('#assignment').val());
    });
    $.each(geometry, function(key,g) {
        $('#tool').append('<option value="'+key+'">'+g.label+'</option>')
    });
    selectedTool('boundingBox');
    $('#tool').change(function() {
        selectedTool($('#tool').val());
    });
    listAssignments();
    $('#label').autocomplete({
        source: function(req,resp) {
            var ass = $('#workspace').data('assignment');
            if(ass == undefined) {
                return;
            }
            $.getJSON('/category_autocomplete/'+ass.mode+'?term='+req.term, function(r) {
                resp($.map(r,function(item) {
                    return {
                        'label': item.label,
                        'value': item.value
                    }
                }));
            });
        },
        minLength: 2
    });
    $('#closeRight').bind('click', function() {
        $('#openRight').show();
        $('#rightPanel').hide(100);
    });
    $('#openRight').bind('click', function() {
        $('#openRight').hide();
        $('#rightPanel').show(100, resizeAll);
    });
    $(window).bind('resize', resizeAll);
    $('#login').authentication(function(username) {
	clog('logged in as '+username);
	$('#workspace').data('login',username);
	$('#next').addClass('hidden');
	$('#prev').addClass('hidden');
    }, function(username) {
	clog('logged out as '+username);
	$('#workspace').removeData('login');
	$('#next').removeClass('hidden');
	$('#prev').removeClass('hidden');
    });
    // substrate
    // FIXME should pick the substrate scope for the assignments' mode
    $('#rightPanel').append('<br><fieldset><legend>Dominant Substrate</legend><div>&nbsp;</div></fieldset>')
	.find('div:last')
	.categoryPicker(1, DOMINANT_SUBSTRATE_SCOPE, queueSubstrateAnnotation);
    $('#rightPanel').append('<br><fieldset><legend>Subdominant Substrate</legend><div>&nbsp;</div></fieldset>')
	.find('div:last')
	.categoryPicker(1, SUBDOMINANT_SUBSTRATE_SCOPE, queueSubstrateAnnotation);
    $('#rightPanel').append('<br><fieldset><legend>Image Notes</legend><div>&nbsp;</div></fieldset>')
	.find('div:last')
	.categoryPicker(1, IMAGE_SCOPE, queueSubstrateAnnotation);
    $('#rightPanel').append('<br><fieldset><legend>Quick Info</legend><div id="quickinfo" ></div></fieldset>')
	.find('div:last')
    gotoPage(page,size);
});
