function scatter_setup(elt, timeseries, pid, width, height) {
    var $this = $(elt);
    var ENDPOINT_PFX = 'data_scat_ep_pfx';
    var ENDPOINT_SFX = 'data_scat_ep_sfx';
    var WIDTH = 'data_scat_ep_width';
    var HEIGHT = 'data_scat_ep_height';
    var PLOT_OPTIONS = 'data_scat_options';
    var PLOT_X_TYPE = 'data_scat_x_plot_type';
    var PLOT_Y_TYPE = 'data_scat_y_plot_type';
    var PLOT_X = 'data_scat_x_axis';
    var PLOT_Y = 'data_scat_y_axis';
    var PLOT_X_OFFSET = 'data_scat_x_offset';
    var PLOT_Y_OFFSET = 'data_scat_y_offset';
    var PLOT_X_AXIS_MIN = 'data_scat_x_axis_min';
    var PLOT_Y_AXIS_MIN = 'data_scat_y_axis_min';
    var PLOT_X_AXIS_MAX = 'data_scat_x_axis_max';
    var PLOT_Y_AXIS_MAX = 'data_scat_y_axis_max';
    var PLOT_DATA = 'data_scat_plot_data';
    var endpointPfx = '/' + timeseries + '/api/plot';
    var endpointSfx = '/pid/';
    $this.data(HEIGHT, height);

    // Hard coded simply because I don't know / want to find out how to pull this from Python where the csv is read. This is easier
    var plotChoices = ['roi_number', 'fluorescenceLow', 'scatteringLow', 'Area', 'Biovolume', 'BoundingBox_xwidth', 'BoundingBox_ywidth', 'ConvexArea', 'ConvexPerimeter', 'Eccentricity', 'EquivDiameter',
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

    // Set some defaults
    var plotTypes = ['linear', 'log'];
    if ($this.data(PLOT_X_TYPE) == undefined) {
        $this.data(PLOT_X_TYPE, plotTypes[0]);
    }
    if ($this.data(PLOT_Y_TYPE) == undefined) {
        $this.data(PLOT_Y_TYPE, plotTypes[0]);
    }
    if ($this.data(PLOT_X) == undefined) {
        $this.data(PLOT_X, 'bottom');
    }
    if ($this.data(PLOT_Y) == undefined) {
        $this.data(PLOT_Y, 'left');
    }
    if ($this.data(PLOT_X_OFFSET) == undefined) {
        $this.data(PLOT_X_OFFSET, 0);
    }
    if ($this.data(PLOT_Y_OFFSET) == undefined) {
        $this.data(PLOT_Y_OFFSET, 0);
    }
    if ($this.data(PLOT_X_AXIS_MIN) == undefined) {
        $this.data(PLOT_X_AXIS_MIN, '');
    }
    if ($this.data(PLOT_X_AXIS_MAX) == undefined) {
        $this.data(PLOT_X_AXIS_MAX, '');
    }
    if ($this.data(PLOT_Y_AXIS_MIN) == undefined) {
        $this.data(PLOT_Y_AXIS_MIN, '');
    }
    if ($this.data(PLOT_Y_AXIS_MAX) == undefined) {
        $this.data(PLOT_Y_AXIS_MAX, '');
    }

    var plot;

    $this.data(PLOT_OPTIONS, {
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
        },
        xaxis: {

        },
        yaxis: {

        }
    });
    var xf = {
        transform: function (v) {
            return v == 0 ? v : Math.log(v);
        },
        inverseTransform: function (v) {
            return Math.exp(v);
        }
    };
    if ($this.data(PLOT_X_TYPE) == 'log') {$this.data(PLOT_OPTIONS).xaxis = xf;}
    if ($this.data(PLOT_Y_TYPE) == 'log') {$this.data(PLOT_OPTIONS).yaxis = xf;}
    // Set ranges to camera size if using bottom or left
    if ($this.data(PLOT_X) == 'bottom') {
        // Don't override transform and inverseTransform possibly set above
        $this.data(PLOT_OPTIONS).xaxis = $this.data(PLOT_OPTIONS).xaxis || {};
        $this.data(PLOT_OPTIONS).xaxis.min = 0;
        $this.data(PLOT_OPTIONS).xaxis.max = 1381;
    }
    if ($this.data(PLOT_Y) == 'left') {
        $this.data(PLOT_OPTIONS).yaxis = $this.data(PLOT_OPTIONS).yaxis || {};
        $this.data(PLOT_OPTIONS).yaxis.min = 0;
        $this.data(PLOT_OPTIONS).yaxis.max = 1035;
    }
    $this.siblings('.bin_view_controls')
        .find('.bin_view_specific_controls')
        .empty()
        .append('<br><br>X Type: <span></span>') // plot type: linear / log
        .find('span:last')
        .radio(plotTypes, function (plotType) {
            return plotType;
        }, $this.data(PLOT_X_TYPE))
        .bind('select', function (event, value) {
            $this.data(PLOT_X_TYPE, value);
             // Careful not to override other xaxis data
             $this.data(PLOT_OPTIONS).xaxis = $this.data(PLOT_OPTIONS).xaxis || {};
             if(value == 'log') {
             $this.data(PLOT_OPTIONS).xaxis.transform = xf.transform;
             $this.data(PLOT_OPTIONS).xaxis.inverseTransform = xf.inverseTransform;
             }
             else {
             // Setting to null defaults it to linear
             $this.data(PLOT_OPTIONS).xaxis.transform = undefined;
             $this.data(PLOT_OPTIONS).xaxis.inverseTransform = undefined;
             }
             // Keep plot reference updated
             plot = $.plot($this, [$this.data(PLOT_DATA)], $this.data(PLOT_OPTIONS));
        });
    $this.siblings('.bin_view_controls')
        .find('.bin_view_specific_controls')
        .append(' &nbsp;Y Type: <span></span>') // plot type: linear / log
        .find('span:last')
        .radio(plotTypes, function (plotType) {
            return plotType;
        }, $this.data(PLOT_Y_TYPE))
        .bind('select', function (event, value) {
            $this.data(PLOT_Y_TYPE, value);
            $this.data(PLOT_OPTIONS).yaxis = $this.data(PLOT_OPTIONS).yaxis || {};
            if(value == 'log') {
                $this.data(PLOT_OPTIONS).yaxis.transform = xf.transform;
                $this.data(PLOT_OPTIONS).yaxis.inverseTransform = xf.inverseTransform;
            }
            else {
                // Setting to null defaults it to linear
                $this.data(PLOT_OPTIONS).yaxis.transform = undefined;
                $this.data(PLOT_OPTIONS).yaxis.inverseTransform = undefined;
            }
            // Keep plot reference updated
            plot = $.plot($this, [$this.data(PLOT_DATA)], $this.data(PLOT_OPTIONS));
        });
    $this.siblings('.bin_view_controls')
        .find('.bin_view_specific_controls')
        .append('X axis: <span></span>') // x axis
        .find('span:last')
        .append('<select id="x_axis_choice" style="width:150px"><option value="bottom">bottom</option></select>');
    $this.siblings('.bin_view_controls')
        .find('.bin_view_specific_controls')
        .append(' Y axis: <span></span>') // y axis
        .find('span:last')
        .append('<select id="y_axis_choice" style="width:150px"><option value="left">left</option></select>');
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
        .append('<br><br>X Data Offset: ')
        .append('<input type="text" style="width:40px" id="x_axis_offset"/>')
        .append(' Y Data Offset: ')
        .append('<input type="text" style="width:40px" id="y_axis_offset"/>')
        .append(' X Axis Min: ')
        .append('<input type="text" style="width:40px" id="x_axis_min"/>')
        .append(' X Axis Max: ')
        .append('<input type="text" style="width:40px" id="x_axis_max"/>')
        .append(' Y Axis Min: ')
        .append('<input type="text" style="width:40px" id="y_axis_min"/>')
        .append(' Y Axis Max: ')
        .append('<input type="text" style="width:40px" id="y_axis_max"/>')
        .append(' &nbsp;&nbsp;&nbsp;<button type="button" id="reset_axes">Reset Axes</button>');

    // Make selections persist through the redrawing of bin display
    document.getElementById('x_axis_offset').value = $this.data(PLOT_X_OFFSET);
    document.getElementById('y_axis_offset').value = $this.data(PLOT_Y_OFFSET);
    document.getElementById('x_axis_choice').value = $this.data(PLOT_X);
    document.getElementById('y_axis_choice').value = $this.data(PLOT_Y);
    document.getElementById('x_axis_min').value = $this.data(PLOT_X_AXIS_MIN);
    document.getElementById('y_axis_min').value = $this.data(PLOT_Y_AXIS_MIN);
    document.getElementById('x_axis_max').value = $this.data(PLOT_X_AXIS_MAX);
    document.getElementById('y_axis_max').value = $this.data(PLOT_Y_AXIS_MAX);

    // Make all these choices update the plot
    $('#x_axis_choice').bind('change', function(e) {
        var val = document.getElementById('x_axis_choice').value;
        $this.data(PLOT_X, val);
        $this.trigger('drawBinDisplay');
    });
    $('#y_axis_choice').bind('change', function(e) {
        var val = document.getElementById('y_axis_choice').value;
        $this.data(PLOT_Y, val);
        $this.trigger('drawBinDisplay');
    });

    $('#x_axis_offset').bind('change', function(e) {
        var val = document.getElementById('x_axis_offset').value;
        if(!isNaN(parseFloat(val)) || val === '') {
            if(val === '') {
                // If they make it blank, reset to 0
                val = 0;
                document.getElementById('x_axis_offset').value = 0;
            }
            var existing_points = $this.data(PLOT_DATA).data;
            var new_points = [];
            for (var j=0; j<existing_points.length; j++) { // Loop and offset
                // First remove the existing offset
                var new_x = +existing_points[j][0] - $this.data(PLOT_X_OFFSET);
                // Then add the new one
                new_x = new_x + +val;
                new_points[j] = [new_x, existing_points[j][1]];
            }
            $this.data(PLOT_DATA).data = new_points;
            $this.data(PLOT_X_OFFSET, val);
            plot = $.plot($this, [$this.data(PLOT_DATA)], $this.data(PLOT_OPTIONS)); // Redraw the plot
        }
    });
    $('#y_axis_offset').bind('change', function(e) {
        var val = document.getElementById('y_axis_offset').value;
        if(!isNaN(parseFloat(val)) || val === '') {
            if(val === '') {
                val = 0;
                document.getElementById('y_axis_offset').value = 0;
            }
            var existing_points = $this.data(PLOT_DATA).data;
            var new_points = [];
            for (var j=0; j<existing_points.length; j++) { // Loop and offset
                // First remove the existing offset
                var new_y = +existing_points[j][1] - $this.data(PLOT_Y_OFFSET);
                // Then add the new one
                new_y = new_y + +val;
                new_points[j] = [existing_points[j][0], new_y];
            }
            $this.data(PLOT_DATA).data = new_points;
            $this.data(PLOT_Y_OFFSET, val);
            plot = $.plot($this, [$this.data(PLOT_DATA)], $this.data(PLOT_OPTIONS)); // Redraw the plot
        }
    });
    $('#x_axis_min').bind('change', function(e) {
        var val = document.getElementById('x_axis_min').value;
        if(!isNaN(parseFloat(val)) || val === '') {
            $this.data(PLOT_X_AXIS_MIN, val);
            // If users reset the boxes to blank, flot should calculate our value
            if(val === '') { val = null; }
            plot.getAxes().xaxis.options.min = val;
            plot.setupGrid(); // Necessary because we changed an axis
            plot.draw();
        }
    });
    $('#x_axis_max').bind('change', function(e) {
        var val = document.getElementById('x_axis_max').value;
        if(!isNaN(parseFloat(val)) || val === '') {
            $this.data(PLOT_X_AXIS_MAX, val);
            if(val === '') { val = null; }
            plot.getAxes().xaxis.options.max = val;
            plot.setupGrid();
            plot.draw();
        }
    });
    $('#y_axis_min').bind('change', function(e) {
        var val = document.getElementById('y_axis_min').value;
        if(!isNaN(parseFloat(val)) || val === '') {
            $this.data(PLOT_Y_AXIS_MIN, val);
            if(val === '') { val = null; }
            plot.getAxes().yaxis.options.min = val;
            plot.setupGrid();
            plot.draw();
        }
    });
    $('#y_axis_max').bind('change', function(e) {
        var val = document.getElementById('y_axis_max').value;
        if(!isNaN(parseFloat(val)) || val === '') {
            $this.data(PLOT_Y_AXIS_MAX, val);
            if(val === '') { val = null; }
            plot.getAxes().yaxis.options.max = val;
            plot.setupGrid();
            plot.draw();
        }
    });
    $('#reset_axes').bind('click', function(e) {
        document.getElementById("x_axis_min").value = '';
        document.getElementById("x_axis_max").value = '';
        document.getElementById("y_axis_min").value = '';
        document.getElementById("y_axis_max").value = '';
        $this.data(PLOT_X_AXIS_MIN, '');
        $this.data(PLOT_X_AXIS_MAX, '');
        $this.data(PLOT_Y_AXIS_MIN, '');
        $this.data(PLOT_Y_AXIS_MAX, '');
        var axes = plot.getAxes();
        // Setting these to null makes flot re-calculate the defaults for the data
        axes.xaxis.options.min = null;
        axes.xaxis.options.max = null;
        axes.yaxis.options.min = null;
        axes.yaxis.options.max = null;
        // But let's keep our camera size as default for bottom/left
        if($this.data(PLOT_X) == 'bottom') {
            axes.xaxis.options.min = 0;
            axes.xaxis.options.max = 1381;
        }
        if($this.data(PLOT_Y) == 'left') {
            axes.yaxis.options.min = 0;
            axes.yaxis.options.max = 1035;
        }
        plot.setupGrid();
        plot.draw();
    })

    $this.unbind('show_bin').bind('show_bin', function (event, bin_pid) {
        // Change plot axes based on min/max values if available
        if ($this.data(PLOT_X_AXIS_MIN) != undefined && $this.data(PLOT_X_AXIS_MIN) !== '') {
            $this.data(PLOT_OPTIONS).xaxis.min = $this.data(PLOT_X_AXIS_MIN);
        }
        if ($this.data(PLOT_X_AXIS_MAX) != undefined && $this.data(PLOT_X_AXIS_MAX) !== '') {
            $this.data(PLOT_OPTIONS).xaxis.max = $this.data(PLOT_X_AXIS_MAX);
        }
        if ($this.data(PLOT_Y_AXIS_MIN) != undefined && $this.data(PLOT_Y_AXIS_MIN) !== '') {
            $this.data(PLOT_OPTIONS).yaxis.min = $this.data(PLOT_Y_AXIS_MIN);
        }
        if ($this.data(PLOT_Y_AXIS_MAX) != undefined && $this.data(PLOT_Y_AXIS_MAX) !== '') {
            $this.data(PLOT_OPTIONS).yaxis.max = $this.data(PLOT_Y_AXIS_MAX);
        }
        var plotParams = params2url({
            'x': $this.data(PLOT_X),
            'y': $this.data(PLOT_Y)
        });
        var endpoint = endpointPfx + plotParams + endpointSfx + bin_pid;
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
                point.x = +point.x + parseFloat($this.data(PLOT_X_OFFSET));
                point.y = +point.y + parseFloat($this.data(PLOT_Y_OFFSET));
                point_data.push([point.x, point.y]);
                roi_pids.push(bin_pid + '_' + point.roi_num);
            });
            $this.data(PLOT_DATA, {
                label: $this.data(PLOT_X) + ' / ' + $this.data(PLOT_Y),
                data: point_data,
                color: "black",
                points: {
                    fillColor: "black"
                },
                highlightColor: "red"
            });
            $this.empty()
                .css('width', $this.data(WIDTH))
                .css('height', $this.data(HEIGHT));
            plot = $.plot($this, [$this.data(PLOT_DATA)], $this.data(PLOT_OPTIONS));
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
