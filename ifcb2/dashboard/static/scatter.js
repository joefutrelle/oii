function scatter_setup(elt, timeseries, pid, width, height) {
    var $this = $(elt);
    var ENDPOINT_PFX = 'data_scat_ep_pfx';
    var ENDPOINT_SFX = 'data_scat_ep_sfx';
    var WIDTH = 'data_scat_ep_width';
    var HEIGHT = 'data_scat_ep_height';
    var PLOT_OPTIONS = 'data_scat_options';
    var PLOT_TYPE = 'data_scat_plot_type';
    var PLOT_X = 'data_scat_x_axis';
    var PLOT_Y = 'data_scat_y_axis';
    var PLOT_X_OFFSET = 'data_scat_x_offset';
    var PLOT_Y_OFFSET = 'data_scat_y_offset';
    var endpointPfx = '/' + timeseries + '/api/plot';
    var endpointSfx = '/pid/';
    $this.data(HEIGHT, height);
    var plotTypes = ['linear', 'log'];
    var plotType = $this.data(PLOT_TYPE);
    if (plotType == undefined) {
        plotType = plotTypes[0];
    }
    // Hard coded simply because I don't know / want to find out how to pull this from Python where the csv is read. This is easier
    var plotChoices = ['roi_number', 'Area', 'Biovolume', 'BoundingBox_xwidth', 'BoundingBox_ywidth', 'ConvexArea', 'ConvexPerimeter', 'Eccentricity', 'EquivDiameter',
        'Extent', 'FeretDiameter', 'H180', 'H90', 'Hflip', 'MajorAxisLength', 'MinorAxisLength', 'Orientation', 'Perimeter', 'RWcenter2total_powerratio', 'RWhalfpowerintegral',
        'Solidity', 'moment_invariant1', 'moment_invariant2', 'moment_invariant3', 'moment_invariant4', 'moment_invariant5', 'moment_invariant6', 'moment_invariant7',
        'numBlobs', 'shapehist_kurtosis_normEqD', 'shapehist_mean_normEqD', 'shapehist_median_normEqD', 'shapehist_mode_normEqD', 'shapehist_skewness_normEqD',
        'summedArea', 'summedBiovolume', 'summedConvexArea', 'summedConvexPerimeter', 'summedFeretDiameter', 'summedMajorAxisLength', 'summedMinorAxisLength',
        'summedPerimeter', 'texture_average_contrast', 'texture_average_gray_level', 'texture_entropy', 'texture_smoothness', 'texture_third_moment',
        'texture_uniformity', 'RotatedArea', 'RotatedBoundingBox_xwidth', 'RotatedBoundingBox_ywidth', 'Area_over_PerimeterSquared', 'Area_over_Perimeter',
        'H90_over_Hflip', 'H90_over_H180', 'Hflip_over_H180', 'summedConvexPerimeter_over_Perimeter', 'rotated_BoundingBox_solidity', ' Wedge01', 'Wedge02',
        'Wedge03', 'Wedge04', 'Wedge05', 'Wedge06', 'Wedge07', 'Wedge08', 'Wedge09', 'Wedge10', 'Wedge11', 'Wedge12', 'Wedge13', 'Wedge14', 'Wedge15', 'Wedge16',
        'Wedge17', 'Wedge18', 'Wedge19', 'Wedge20', 'Wedge21', 'Wedge22', 'Wedge23', 'Wedge24', 'Wedge25', 'Wedge26', 'Wedge27', 'Wedge28', 'Wedge29', 'Wedge30',
        'Wedge31', 'Wedge32', 'Wedge33', 'Wedge34', 'Wedge35', 'Wedge36', 'Wedge37', 'Wedge38', 'Wedge39', 'Wedge40', 'Wedge41', 'Wedge42', 'Wedge43', 'Wedge44',
        'Wedge45', 'Wedge46', 'Wedge47', 'Wedge48', 'Ring01', 'Ring02', 'Ring03', 'Ring04', 'Ring05', 'Ring06', 'Ring07', 'Ring08', 'Ring09', 'Ring10',
        'Ring11', 'Ring12', 'Ring13', 'Ring14', 'Ring15', 'Ring16', 'Ring17', 'Ring18', 'Ring19', 'Ring20', 'Ring21', 'Ring22', 'Ring23', 'Ring24', 'Ring25',
        'Ring26', 'Ring27', 'Ring28', 'Ring29', 'Ring30', 'Ring31', 'Ring32', 'Ring33', 'Ring34', 'Ring35', 'Ring36', 'Ring37', 'Ring38', 'Ring39', 'Ring40',
        'Ring41', 'Ring42', 'Ring43', 'Ring44', 'Ring45', 'Ring46', 'Ring47', 'Ring48', 'Ring49', 'Ring50', 'HOG01', 'HOG02', 'HOG03', 'HOG04', 'HOG05', 'HOG06',
        'HOG07', 'HOG08', 'HOG09', 'HOG10', 'HOG11', 'HOG12', 'HOG13', 'HOG14', 'HOG15', 'HOG16', 'HOG17', 'HOG18', 'HOG19', 'HOG20', 'HOG21', 'HOG22', 'HOG23',
        'HOG24', 'HOG25', 'HOG26', 'HOG27', 'HOG28', 'HOG29', 'HOG30', 'HOG31', 'HOG32', 'HOG33', 'HOG34', 'HOG35', 'HOG36', 'HOG37', 'HOG38', 'HOG39', 'HOG40', 'HOG41',
        'HOG42', 'HOG43', 'HOG44', 'HOG45', 'HOG46', 'HOG47', 'HOG48', 'HOG49', 'HOG50', 'HOG51', 'HOG52', 'HOG53', 'HOG54', 'HOG55', 'HOG56', 'HOG57', 'HOG58', 'HOG59', 'HOG60',
        'HOG61', 'HOG62', 'HOG63', 'HOG64', 'HOG65', 'HOG66', 'HOG67', 'HOG68', 'HOG69', 'HOG70', 'HOG71', 'HOG72', 'HOG73', 'HOG74', 'HOG75', 'HOG76', 'HOG77', 'HOG78', 'HOG79',
        'HOG80', 'HOG81'];

    // var plotXs = ['bottom', 'fluorescenceLow'];
    var plotX = $this.data(PLOT_X);
    if (plotX == undefined) {
        plotX = 'bottom'
    }
    // var plotYs = ['left', 'scatteringLow'];
    var plotY = $this.data(PLOT_Y);
    if (plotY == undefined) {
        plotY = 'left'
    }
    var plotXOffset = $this.data(PLOT_X_OFFSET) || 0;
    var plotYOffset = $this.data(PLOT_Y_OFFSET) || 0;

    var plotOptions = {
        series: {
            points: {
                show: true,
                radius: 2,
            }
        },
        grid: {
            clickable: true,
            hoverable: true,
            autoHighlight: true
        },
        zoom: {
            interactive: true
        },
        pan: {
            interactive: true,
            frameRate: 60
        },
        selection: {
            mode: "xy",
            color: "red"
        }
    };
    if (plotType == 'log') {
        var xf = {
            transform: function (v) {
                return v == 0 ? v : Math.log(v);
            },
            inverseTransform: function (v) {
                return Math.exp(v);
            }
        };
        plotOptions.xaxis = xf;
        plotOptions.yaxis = xf;
    }
    else if (plotType == 'linear') {
        if (plotX == 'bottom') {
            plotOptions.xaxis = {
                min: 0,
                max: 1381
            }
        }
        if (plotY == 'left') {
            plotOptions.yaxis = {
                min: 0,
                max: 1035
            }
        }
    }
    $this.data(PLOT_OPTIONS, plotOptions);
    $this.siblings('.bin_view_controls')
        .find('.bin_view_specific_controls')
        .empty()
        .append('<br><br>Type: <span></span>') // plot type: linear / log
        .find('span:last')
        .radio(plotTypes, function (plotType) {
            return plotType;
        }, plotType).bind('select', function (event, value) {
            $this.data(PLOT_TYPE, value);
            $this.trigger('drawBinDisplay');
        });
    $this.siblings('.bin_view_controls')
        .find('.bin_view_specific_controls')
        .append('X axis: <span></span>') // x axis
        .find('span:last')
        .append('<select id="x_axis_choice" style="width:150px"><option value="bottom">bottom</option>' +
        '<option value="fluorescenceLow">fluorescenceLow</option></select>');
        /*.radio(plotXs, function (plotX) {
            return plotX;
        }, plotX).bind('select', function (event, value) {
            $this.data(PLOT_X, value);
            $this.trigger('drawBinDisplay');
        })*/
    $this.siblings('.bin_view_controls')
        .find('.bin_view_specific_controls')
        .append(' Y axis: <span></span>') // y axis
        .find('span:last')
        .append('<select id="y_axis_choice" style="width:150px"><option value="left">left</option>' +
        '<option value="scatteringLow">scatteringLow</option></select>');
        /*.radio(plotYs, function (plotY) {
            return plotY;
        }, plotY).bind('select', function (event, value) {
            $this.data(PLOT_Y, value);
            $this.trigger('drawBinDisplay');
        });*/
    for (var i=0; i<plotChoices.length; i++) {
        // Each select needs its own option elements
        var choice = document.createElement("option");
        var choice_y = document.createElement("option");
        choice.value = plotChoices[i];
        choice_y.value = plotChoices[i];
        choice.text = plotChoices[i];
        choice_y.text = plotChoices[i];
        document.getElementById('x_axis_choice').add(choice);
        document.getElementById('y_axis_choice').add(choice_y)
    }
    $this.siblings('.bin_view_controls')
        .find('.bin_view_specific_controls')
        .append('<br><br>X Axis Offset: ')
        .append('<input type="text" style="width:40px" id="x_axis_offset"/>')
        .append(' Y Axis Offset: ')
        .append('<input type="text" style="width:40px" id="y_axis_offset"/>');

    // Make selections persist through the redrawing of bin display
    document.getElementById('x_axis_offset').value = plotXOffset;
    document.getElementById('y_axis_offset').value = plotYOffset;
    document.getElementById('x_axis_choice').value = plotX;
    document.getElementById('y_axis_choice').value = plotY;

    // Make all these choices update the plot
    $('#x_axis_choice').bind('change', function(e) {
        var val = document.getElementById('x_axis_choice').value;
        plotX = val;
        $this.data(PLOT_X, val);
        $this.trigger('drawBinDisplay');
    });
    $('#y_axis_choice').bind('change', function(e) {
        var val = document.getElementById('y_axis_choice').value;
        plotY = val;
        $this.data(PLOT_Y, val);
        $this.trigger('drawBinDisplay');
    });

    $('#x_axis_offset').bind('change', function(e) {
       var val = document.getElementById('x_axis_offset').value;
        if(!isNaN(val)) {
            val = parseFloat(val);
            plotXOffset = val;
            $this.data(PLOT_X_OFFSET, val);
            $this.trigger('drawBinDisplay');
        }
    });
    $('#y_axis_offset').bind('change', function(e) {
       var val = document.getElementById('y_axis_offset').value;
        if(!isNaN(val)) {
            val = parseFloat(val);
            plotYOffset = val;
            $this.data(PLOT_Y_OFFSET, val);
            $this.trigger('drawBinDisplay');
        }
    });
    $this.unbind('show_bin').bind('show_bin', function (event, bin_pid) {
        var plotParams = params2url({
            'x': plotX,
            'y': plotY
        });
        var endpoint = endpointPfx + plotParams + endpointSfx + bin_pid;
        var plot_options = $this.data(PLOT_OPTIONS);
        console.log("Loading " + endpoint + "...");
        $.getJSON(endpoint, function (r) {
            console.log("Got JSON data");
            var bin_pid = r.bin_pid;
            var roi_pids = [];
            var point_data = [];
            // Handle old IFCB2 format issue where values are negative
            var inverse_x = false;
            var inverse_y = false;
            if(bin_pid.indexOf("/IFCB2")) {
                console.log("Old file format, inversing fluorescence and scattering values...")
                if (r.x_axis_label == "fluorescenceLow" || r.x_axis_label == "scatteringLow") {
                    inverse_x = true;
                }
                if (r.y_axis_label == "fluorescenceLow" || r.y_axis_label == "scatteringLow") {
                   inverse_y = true;
                }
            }
            $.each(r.points, function (ix, point) {
                if(inverse_x)
                    point.x = point.x * -1;
                if(inverse_y)
                    point.y = point.y * -1;
                // Offset points by user value
                // These need a "+" prefix or else JS interprets them as strings
                // Despite the math right above??
                point.x = +point.x + parseFloat(plotXOffset);
                point.y = +point.y + parseFloat(plotYOffset);
                point_data.push([point.x, point.y]);
                roi_pids.push(bin_pid + '_' + point.roi_num);
            });
            var plot_data = {
                label: plotX + ' / ' + plotY,
                data: point_data,
                color: "black",
                points: {
                    fillColor: "black"
                },
                highlightColor: "red"
            };
            $this.empty()
                .css('width', $this.data(WIDTH))
                .css('height', $this.data(HEIGHT))
                .plot([plot_data], plot_options);
            $this.data('roi_pids', roi_pids);
            $this.data('point_data', point_data);
        });
        $this.bind("plotselected", function (evt, ranges) {
            console.log(evt);
            $(evt.target).addClass("plotselected");//not sure what this does
            // receive selection range from event
            lo_x = ranges.xaxis.from;
            hi_x = ranges.xaxis.to;
            lo_y = ranges.yaxis.from;
            hi_y = ranges.yaxis.to;
            // replace the roi image view with this mosaic view
            $('#roi_image').empty()
                .closeBox()
                .css('display', 'inline-block')
                .css('width', '45%');
            // for each point on the scatter plot
            var total_displayed = 0;
            $.each($this.data('point_data'), function (ix, point) {
                var x = point[0];
                var y = point[1];
                // if it's in the selection rectangle
                if (x >= lo_x && x <= hi_x && y >= lo_y && y <= hi_y) {
                    if (total_displayed >= 50) {
                        return false; // break the each loop
                    }
                    // draw the roi
                    total_displayed++;
                    var pid = $this.data('roi_pids')[ix];
                    console.log("adding pid: " + pid);
                    $('#roi_image').append('<a href="' + pid + '.html" target="_blank"><img src="' + pid + '.jpg"></img></a>');
                }
            });
        });
        $this.bind("plotclick", function (evt, pos, item) {
            console.log(evt);
            if ($(evt.target).hasClass("plotselected")) {
                $(evt.target).removeClass("plotselected");
                return;
            } else if (item) {
                var roi_pids = $this.data('roi_pids');
                if (!roi_pids) {
                    return
                }
                ;
                roi_pid = roi_pids[item.dataIndex];
                // fire a roi clicked event
                $this.trigger('roi_click', roi_pid);
            }
        })
        $this.bind("plotpan", function (event, plot) {
            plot.clearSelection(true);
        });
        $this.bind("plotzoom", function (event, plot) {
            plot.clearSelection(true);
        });
    });
}
//jquery plugin
(function ($) {
    $.fn.extend({
        scatter: function (timeseries, pid, width, height) {
            return this.each(function () {
                var $this = $(this);
                $this.css('width', width)
                    .css('height', height);
                scatter_setup($this, timeseries, pid, width, height);
                console.log('triggering show_bin for scatter');
                $this.trigger('show_bin', [pid]);
            });//each
        }//scatter
    });//$.fn.extend
})(jQuery);//end of plugin
