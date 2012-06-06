auth = {};
auth.challenge = function(element, callback) {
    $(element).append('Username: <input id="auth_username"> Password: <input type="password" id="auth_password"> <a href="#" id="auth_login" class="button">Login</a>')
	.find('.button').button()
	.end()
	.find('#auth_login')
	.click(function() {
	    $.ajax({
		url: '/authenticate',
		type: 'POST',
		dataType: 'json',
		data: {
		    'username': $('#auth_username').val(),
		    'password': $('#auth_password').val()
		},
		success: function(data) {
		    callback(data.username);
		},
		failure: function() {
		    alert('wrong credentials. no cookie for you!');
		}
	    });
	});
};