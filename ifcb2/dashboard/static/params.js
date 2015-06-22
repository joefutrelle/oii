function params2url(params) {
    var url = '';
    for(var key in params) {
	if(params.hasOwnProperty(key)) {
	    url += '/' + key + '/' + params[key];
	}
    }
    return url;
}
function url2params(url) {
    var params = {};
    var key = undefined;
    for(var seg in url.split('/')) {
	if(key==undefined) {
	    key=seg;
	} else {
	    params[key] = seg;
	    key = undefined;
	}
    }
    return params;
}
