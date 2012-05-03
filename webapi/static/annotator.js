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
            drawImage(cell);
            drawPendingAnnotations(cell);
            drawExistingAnnotations(cell);
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
function drawExistingAnnotations(cell) {
    $.get('/list_annotations/image/' + $(cell).data('imagePid'), function(r) {
        clearImageLayer(cell,'existing');
        var ctx = getImageLayerContext(cell,'existing');
        $(r).each(function(ix,ann) {
            showAnnotationGeometry(ctx,ann);
        });
    });
}
//cell - div with image in it
//ann - annotation
function showAnnotationGeometry(ctx,ann) {
    // FIXME support zoom
    // use the appropriate drawing method to draw any geometry found
    clog('drawing existing for '+JSON.stringify(ann));
    if('geometry' in ann) {
        var g = ann.geometry;
        for(key in ann.geometry) {
            var g = ann.geometry[key];
            if(g != undefined) {
                clog('attempting to draw a '+key+' for '+JSON.stringify(ann.geometry[key]));
                geometry[key].draw(ctx, ann.geometry[key]);
            }
        }
    }
}
function addCell(imagePid) {
    return $('#images').append('<div class="thumbnail"><div class="spacer"></div><div class="caption ui-widget">&nbsp;</div><div class="subcaption ui-widget"></div></div>')
        .find('div.thumbnail:last')
        .data('imagePid',imagePid)
        .disableSelection();
}
function gotoPage(page,size) {
    if(page < 1) page = 1;
    clog('going to page '+page);
    var images = $('#workspace').data('images')
    if(images == undefined) {
        return;
    }
    clearPage();
    var offset = (page-1) * size;
    var limit = offset + size;
    $.each(images, function(i,entry) {
        if(i >= offset && i < limit) {
            // append image with approprite URL
            var imageUrl = entry.image;
            var imagePid = entry.pid; // for now, pid = url
            // each cell has the following data associted with it:
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
        } // paging condition in loop over images
    }); // loop over images
}
function drawPendingAnnotations(cell) {
    var imagePid = $(cell).data('imagePid');
    var p = pending()[imagePid];
    if(p != undefined) {
        var cat = categoryLabelForPid(p.category);
        var ctx = getImageLayerContext(cell,'pending');
        showAnnotationGeometry(ctx,p);
        clog('selecting '+cat+' for '+imagePid);
        select(cell, cat);
    }
}
/*
function drawExistingAnnotations(cell) {
    var imagePid = $(cell).data('imagePid');
    var ctx = getImageLayerContext(cell,'existing');
    $.ajax({
        url: '/list_annotations/image/' + imagePid,
        dataType: 'json',
        success: function(r) {
            ctx.clearRect(0,0,$(cell).data('scaledWidth'),$(cell).data('scaledHeight'));
            var anns = {};
            $(r).each(function(ix,ann) {
                showAnnotationGeometry(ctx,ann);
                if(!(ann.category in anns)) {
                    anns[ann.category] = 1;
                } else {
                    anns[ann.category] += 1;
                }
            });
            // now we show which annotation has the most "votes"
            var max = 0;
            var theLabel = '';
            var ex = '';
            for(var cat in anns) {
                var label = categoryLabelForPid(cat);
                ex += ' ' + label;
                if(anns[cat] > max) {
                    max = anns[cat];
                    theLabel = label;
                }
                if(anns[cat] > 1) {
                    ex += '&nbsp;x' + anns[cat];
                }
            }
            if(theLabel != '') {
                setLabel(cell,theLabel);
                $(cell).find('.subcaption').html(ex);
            }
        }
    });
}
*/
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
function preCommit() {
    /* generate an ID for each annotation */
    var n = 0;
    for(var k in pending()) { n++; }
    var i = n-1;
    /* FIXME hardcoded namespace */
    with_json_request('/generate_ids/'+n+'/http://foobar.ns/ann_', function(r) {
        $.each(pending(), function(imagePid, ann) {
            pending()[imagePid].pid = r[i--];
        });
        commit();
    });
}
function queueAnnotation(ann) {
    ann.annotator = 'http://people.net/joeblow';
    ann.timestamp = iso8601(new Date());
    clog('enqueing '+JSON.stringify(ann));
    pending()[ann.image] = ann;
}
function commit() {
    clog('committing...');
    var as = [];
    $.each(pending(), function(imagePid, ann) {
        as.push(ann)
        clog(ann.image+' is a '+ann.category+' at '+ann.timestamp+', ann_id='+ann.pid);
    });
    $.ajax({
        url: '/create_annotations',
        type: 'POST',
        contentType: 'json',
        dataType: 'json',
        data: JSON.stringify(as),
        success: function() {
            $('div.thumbnail.selected').each(function(ix,cell) {
                commitCell(cell);
                drawExistingAnnotations(cell);
            });
            postCommit();
        }
    });
}
function postCommit() {
    $('#workspace').data('pending',{});
    $(document).trigger('commit','Notify any listeners of a commit');

}
function deselectAll() {
    $('#workspace').data('pending',{});
    $('div.thumbnail.selected').each(function(ix,cell) {
        toggleSelected(cell);
    });
}
function listAssignments() {
    $('#assignment').append('<option value="">Select an Assignment</option>')
    with_json_request('/list_assignments', function(r) {
        $.each(r.assignments, function(i,a) {
            clog(a);
            $('#assignment').append('<option value="'+a.pid+'">'+a.label+'</option>')
        });
    });
}
function changeAssignment(ass_pid) {
    $('#label').val('');
    var ass_pid = $('#assignment').val();
    clog('user selected assignment '+ass_pid);
    if( ass_pid.length > 0 ){
        with_json_request('/fetch_assignment/'+ass_pid, function(r) {
          clog('fetched assignment '+ass_pid);
            $('#workspace').data('assignment',r);
            $('#workspace').data('images',r.images);
            with_json_request('/list_categories/'+r.mode, function(c) {
                clog('fetched categories for mode '+r.mode);
                $('#workspace').data('categories',c);
                gotoPage(1,25);
            });
        });
    }
    $(document).trigger('changeAssignment','Notify any listeners of an assignment change');
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
$(document).ready(function() {
    page = 1;
    size = 20;
    $('#workspace').data('pending',{}); // pending annotations by pid
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
        gotoPage(page,25);
    });
    $('#next').click(function() {
        page++;
        gotoPage(page,25);
    });
    $('#commit').click(function() {
        preCommit();
    });
    $('#cancel').click(function() {
        deselectAll();
    });
    $('#assignment').change(function() {
        changeAssignment($('#assignment').val());
    });
    //$('#tool').append('<option value="">Select a Tool</option>')
    $.each(geometry, function(key,g) {
        $('#tool').append('<option value="'+key+'">'+g.label+'</option>')
    });
    selectedTool('boundingBox');
    $('#tool').change(function() {
        selectedTool($('#tool').val());
    });
    listAssignments();
    gotoPage(page,size);
    $('#label').autocomplete({
        source: function(req,resp) {
            var ass = $('#workspace').data('assignment');
            if(ass == undefined) {
                return;
            }
            with_json_request('/category_autocomplete/'+ass.mode+'?term='+req.term, function(r) {
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
});
function resizeAll() {
    // resize the right panel
    var rp = $('#rightPanel');
    if(rp.is(':visible')) {
        rp.height($(window).height() - ((rp.outerHeight() - rp.height()) + (rp.offset().top * 2)));
    }
}