function createMap(target) {
    // create map based on MapQuest satellite layer
    var mqLayer = new ol.layer.Tile({
	source: new ol.source.OSM()
    });
    // center of the universe is Woods Hole MA
    var woho = ol.proj.transform([-70.661810, 41.526994], 'EPSG:4326', 'EPSG:3857');
    var aView = new ol.View({
	center: woho,
	zoom: 4
    });
    var map = new ol.Map({
	target: target // id of map div
    });
    map.addLayer(mqLayer);
    map.setView(aView);
    return map;
}

function createVectorLayer(map) {
    layer = new ol.layer.Vector({
	source: new ol.source.Vector({})
    });
    map.addLayer(layer);
    return layer;
}

function drawMultipoint(wkt, color, map, vectorLayer) {
    // draw a multipoint given wkt name and color on the feature overlay
    var format = new ol.format.WKT({
	defaultDataProjection: 'ESPG:4326'
    });
    var geom = format.readGeometry(wkt);
    geom.transform('EPSG:4326', 'EPSG:3857');
    var feature = new ol.Feature({
	geometry: geom
    });
    feature.setStyle(new ol.style.Style({
	image: new ol.style.Circle({
	    radius: 2,
	    fill: new ol.style.Fill({
		color: color
	    })
	})
    }));
    vectorLayer.getSource().addFeature(feature);
}

function drawTimeseries(tsLabel, map, vectorLayer) {
    $.getJSON('/'+tsLabel+'/api/geo/points.json', function(r) {
	wkt = r.points;
	drawMultipoint(wkt, '#ff0000', map, vectorLayer);
	var extent = vectorLayer.getSource().getExtent();
	map.getView().fit(extent, map.getSize());
    });
}
