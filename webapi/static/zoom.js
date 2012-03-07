$(document).ready(function() {
    var imageUrl = 'http://www.schneertz.com/schneertzHD.png';
    $('#cell').prepend('<img style="display:none" src="'+imageUrl+'">')
        .find('img')
        .bind('load', {
            cell: cell
        }, function(event) {
            var width = $(this).width();
            var height = $(this).height();
        }
});