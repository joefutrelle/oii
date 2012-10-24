// FIXME add comments
// FIXME scope IDs should not be hardcoded in Javascript layer
var TARGET_SCOPE=1;
var IMAGE_SCOPE=2;
var DOMINANT_SUBSTRATE_SCOPE=3;
var SUBDOMINANT_SUBSTRATE_SCOPE=4;
// FIXME move to CSS
var PENDING_COLOR='#00ff33';
var EXISTING_COLOR='#ffff99';
// accessors for workspace data structure
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
	emptyExistingLi();
    $.get('/list_annotations/image/' + $(cell).data('imagePid'), function(r) {
        clearImageLayer(cell,'existing');
        var ctx = getImageLayerContext(cell,'existing');
        var counter = 0;
        clog("about to draw existing annotations...");
	$(cell).data('existing',[]);
        $(r).each(function(ix,ann) {
            existing(cell)[counter++] = ann;
	    addExistingLi(ann);
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

	    changeImageStatus('in+progress');

        }); // loop over images

	//if user has the lock button selected don't reset image notes
	if( $('fieldset:has(div#imageNotes) button.lock ').hasClass('selected')){
		//do nothing	
	} else{
		$('#imageNotes').find('.resetButton').click();
		$('#workspace').data('imageNotes',{});
	}
	
    });

    var num_images = $('#workspace').data('assignment').num_images;
    var percent_done = 100*offset/num_images;
    $("#quickOffset").html(offset);
    $("#quickNumImages").html(num_images);
    $("#quickProgress").html(Math.round(percent_done,1) + '%');
    $("#quickAssignment").html(
		"</br>"  + $('#workspace').data('assignment').project_name 
		+ "</br>" + $('#workspace').data('assignment').site_description
		+ "</br>" + $('#workspace').data('assignment').comment
    ) 

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
// FIXME misleadingly named: also commits
function preCommit() {
    generateIds(pending(), commit);
}
function queueAnnotation(cell, geometry) {
    var lv = $('#label').val();
    var c = categoryPidForLabel(lv);
    if(c == undefined) {
	alert(lv+' is not a known category');
    } else {
	var ann = {
            image: $(cell).data('imagePid'),
            category: c,
            geometry: geometry,
	    scope: TARGET_SCOPE,
	    annotator: 'http://people.net/joeblow',
	    timestamp: iso8601(new Date()),
	    assignment: $('#workspace').data('assignment').pid
	};
	pushAnnotation(ann);
    }
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
    $('div.thumbnail').each(function(i, cell) {
	var imagePid = $(cell).data('imagePid');
	$.each($('#workspace').data('dominantSubstrate'), function(ignore, anns) {
	    $.each(anns, function(ix, ann) {
		ann.image = imagePid;
		HOL.add(gi, imagePid, ann);
		as.push(ann);
		clog(ann.image+' is has dominant substrate '+ann.category+' at '+ann.timestamp+', ann_id='+ann.pid);
	    });
	});
	$.each($('#workspace').data('subdominantSubstrate'), function(ignore, anns) {
	    $.each(anns, function(ix, ann) {
		ann.image = imagePid;
		HOL.add(gi, imagePid, ann);
		as.push(ann);
		clog(ann.image+' is has subdominant substrate '+ann.category+' at '+ann.timestamp+', ann_id='+ann.pid);
	    });
	});
	$.each($('#workspace').data('imageNotes'), function(ignore, anns) {
	    $.each(anns, function(ix, ann) {
		ann.image = imagePid;
		HOL.add(gi, imagePid, ann);
		as.push(ann);
		clog(ann.image+' is has imagenotes '+ann.category+' at '+ann.timestamp+', ann_id='+ann.pid);
	    });
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
// clear pending annotations and deselect all cells
function deselectAll() {
    $('#workspace').data('pending',{});
    $('div.thumbnail.selected').each(function(ix,cell) {
        toggleSelected(cell);
    });
    $(document).trigger('canvasChange'); // update cell layers
}
function listAssignments() {
    $('#assignment').append('<option value="">Select an Assignment</option>')
    $.getJSON('/list_assignments', function(r) {
        $.each(r.assignments, function(i,a) {
            $('#assignment').append('<option value="'+a.pid+'">'+elide(a.label,40)+'</option>')
        });
    });
}
// FIXME #1542 need to change offset accordingly etc
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
// this is called on commit
function resetPending() {
    $('#workspace').data('pending',{}); // pending annotations by pid
    $('#workspace').data('undo',[]); // stack of imagePids indicating the order in which anns were queued
}
// this is not called on commit; it's just called initially to populate these data structures
function resetImageLevelPending() {
    $('#workspace').data('dominantSubstrate',{}); // pending substrate annotations by pid
    $('#workspace').data('subdominantSubstrate',{}); // pending substrate annotations by pid
    $('#workspace').data('imageNotes',{});
}
// FIXME make class selection a plugin
function validateLabel() {
    var label = $('#label').val();
    var c = categoryPidForLabel(label);
    if(c == undefined) {
	console.log(label+' invalid');
	$('#label').addClass('invalid');
    } else {
	console.log(label+' valid');
	$('#label').removeClass('invalid');
    }
}
// FIXME should record which annotator changed the status
function changeImageStatus(status){
	    //set status of image to waiting for review on next new
	    if($('#workspace').data('login') != undefined) {
		var imagePid = $(cell).data('imagePid');
		var assignment = getWorkspace('assignment');
		var assignment_pid = assignment.pid;
		$.getJSON('/set_status/image/'+encodeURIComponent(imagePid)
			+'/status/' + status + '/assignment/'+assignment_pid,function(r) {
		   clog('status changed to ' + status + ' for '+imagePid);
		});
	    }
}
// FIXME document.ready is huge
$(document).ready(function() {
    page = 1;
    size = 1;
    // set up annotation tracking data structures
    resetPending();
    resetImageLevelPending();
    $('#workspace').data('showExisting',1); // whether to display existing annotations
    // inputs are ui widget styled
    $('input').addClass('ui-widget'); // FIXME should be "live"?
    // images div is not text-selectable
    $('#images').disableSelection(); // note that this is a jQuery UI function
    // images are not draggable
    $('img').live('mousedown',function(event) {
        event.preventDefault();
    });
    $('a.button').button(); // jQuery UI
    // paging controls: previous
    $('#prev').click(function() {
        page--;
        if(page < 1) page = 1;
        gotoPage(page,size);
    });
    // paging controls: input page as a number
    $('#offset').change(function() {
	page = parseInt($('#offset').val())+1;
	gotoPage(page,size);
    });
    // paging controls: next
    $('#next').click(function() {
	page++;
	gotoPage(page,size);
    });
    // go to "next new" image
    $('#nextNew').click(function() {
	// change current image status before moving to next one
	changeImageStatus('waiting+for+review');
	// commit (not just pre-commit) all non-substrate annotations
	preCommit();
	// commit substrate annotations
	commitSubstrate(function() { // and then,
	    // find the next new image
	    findNewImage(function(pp) { // and then,
		page = pp;
		gotoPage(page,size); // go to it
	    });
	});
    });

    $('#commit').click(function() {
        preCommit(); // commit
    });
    $('#cancel').click(function() {
        deselectAll(); // cancel pending annotations
    });
    $('#undo').click(function() {
        undo(); // undo one annotation
    });

    $(document).bind('keydown', 'ctrl+z', undo); // use ctrl+z for undo

    // "geometry" is the global object with all the geometric types in it
    // defined in geometry.js
    // here, populate a menu with their names
    $.each(geometry, function(key,g) {
        $('#tool').append('<option value="'+key+'">'+g.label+'</option>')
    });
    selectedTool('boundingBox'); // default tool is bounding box
    $('#tool').change(function() { // use the dropdown to select it
        selectedTool($('#tool').val());
    });
    listAssignments(); // request assignments from server FIXME why not later?
    $('#label').autocomplete({ // "label" is class label and it autocompletes
        source: function(req,resp) {
            var ass = $('#workspace').data('assignment');
            if(ass == undefined) {
                return;
            }
	    // autocomplete from this endpoint
            $.getJSON('/category_autocomplete/'+ass.mode+'?term='+req.term, function(r) {
                resp($.map(r,function(item) {
                    return {
                        'label': item.label,
                        'value': item.value
                    }
                }));
            });
        },
        minLength: 2 // user must type at least 2 characters
    });
    $('#label').change(validateLabel); // when a new label is selected, validate it
    // UI controls for opening and closing the right panel
    $('#closeRight').bind('click', function() {
        $('#openRight').show();
        $('#rightPanel').hide(100);
    });
    $('#openRight').bind('click', function() {
        $('#openRight').hide();
        $('#rightPanel').show(100, resizeAll);
    });
    $(window).bind('resize', resizeAll);
    // make the login control using authentication.js
    $('#login').authentication(function(username) { // on login,
	clog('logged in as '+username);
	// record the username in the workspace
	$('#workspace').data('login',username); // FIXME use accessor
	// hide page controls except "next new"
	$('#next').addClass('hidden');
	$('#prev').addClass('hidden');
    }, function(username) { // on logout,
	clog('logged out as '+username);
	// erase the username from the workspace
	$('#workspace').removeData('login'); // FIXME user accessor
	// and unhide all paging controls
	$('#next').removeClass('hidden');
	$('#prev').removeClass('hidden');
    });
       
    // substrate
    // FIXME should pick the substrate scope for the assignments' mode
    // FIXME lots of tiles
    // add dominant substrate category picker
    $('#rightPanel').append('<br><fieldset class="categoryPicker" ><legend>Dominant Substrate</legend><div>&nbsp;</div></fieldset>')
	.find('div:last')
	.categoryPicker(1, DOMINANT_SUBSTRATE_SCOPE, queueSubstrateAnnotation);
    // add subdominant substrate category picker
    $('#rightPanel').append('<br><fieldset class="categoryPicker" ><legend>Subdominant Substrate</legend><div>&nbsp;</div></fieldset>')
	.find('div:last')
	.categoryPicker(1, SUBDOMINANT_SUBSTRATE_SCOPE, queueSubstrateAnnotation);
    // add image notes category picker
    $('#rightPanel').append('<br><fieldset class="categoryPicker" ><legend>Image Notes</legend><div id="imageNotes">&nbsp;</div></fieldset>')
        .find('div:last')
	.categoryPicker(1, IMAGE_SCOPE, queueSubstrateAnnotation);
 $('#rightPanel').append('<br><fieldset ><legend>Assignment</legend> <select id="assignment"></select></fieldset>')
        .find('div:last');

    // add "quick info" panel showing image and assignment metadata
    $('#rightPanel').append('<br><fieldset><legend>Quick Info</legend><div id="quickinfo" ></div></fieldset>')
	.find('div:last');

    // add "existing annotations" control
    $('#rightPanel').append('<br><fieldset><legend>Existing Annotations</legend><div id="existingAnnotations" ></div></fieldset>')
	.find('div:last');

    // when the user changes the assignment
    $('#assignment').change(function() {
        changeAssignment($('#assignment').val()); // deal with it
    });

    // hide existing annotations
    // FIXME
    $('#controls').append('<button href="#" id="toggleExisting" class="button toggle">Hide Existing</a>');
    $('#toggleExisting').click(function() {
	toggleExisting();
    });


//adding toggle buttons to right panel fieldsets
	$('#rightPanel :not(.categoryPicker) legend')
		.append(' <button class="button showhide toggle">show/hide</button>');

	//applies to all category pickers
	//$('.categoryPicker legend').append(' <button  class="button lock toggle">lock</button>');

	$('fieldset:has(div#imageNotes) legend ').append(' <button  class="button lock toggle">lock</button>');

	$('.showhide').click(function(){
		 $(this).parent().siblings().slideToggle("fast");		
	});

	$('.toggle').click(function(){
	 $(this).toggleClass('selected');
	});	

	    $('#rightPanel fieldset:contains("Existing Annotations")').append('<span id="select-result" class="hidden"></span><ol class="selectable"></ol>')
        .find('div:last');

	$('#rightPanel fieldset:contains("Existing Annotations") legend').append('<button  class="button lock toggle" id="deprecate-button">Deprecate</button>');


	$('#deprecate-button').bind('click', function() {		
	 	$("li.ui-selected ").each(function() {		
			var pid = $(this).attr('id');
			clog('DEPRECATING:' +pid);
			
		    $.getJSON('/deprecate/annotation/'+pid, function(r) {
			clog('Deprecated - Response: ' + r );
		    });
		});
	});

$( ".selectable" ).selectable({
			stop: function() {
				var result = $( "#select-result" ).empty();
				$( ".ui-selected", this ).each(function() {
					var pid = $(this).attr('id');
					result.append( pid + '<br/>' );
				});
			}
		});

    gotoPage(page,size);


});
