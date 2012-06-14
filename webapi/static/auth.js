(function($) {
    $.fn.extend({
	authentication: function(callback) {
	    return this.each(function() {
		var $this = $(this);
		$this.empty()
		    .append('Username: <input class="auth_username"> Password: <input type="password" class="auth_password"> <a href="#" class="auth_login button">Login</a>')
		    .find('.button').button()
		    .end()
		    .find('.auth_login')
		    .click(function() {
			$.ajax({
			    url: '/login',
			    type: 'POST',
			    dataType: 'json',
			    data: {
				'username': $this.find('.auth_username').val(),
				'password': $this.find('.auth_password').val()
			    },
			    success: function(data) {
				callback(data.username);
				$this.empty()
				    .append('Logged in as '+data.username+' <a href="#" class="auth_logout button">Logout</a>')
				    .find('.button').button()
				    .end()
				    .find('.auth_logout').click(function () {
					$.getJSON('/logout');
					$this.authentication(callback);
				    });
			    },
			    failure: function() {
				alert('wrong credentials. no cookie for you!');
			    }
			});
		    });
	    });
	}
    });
})(jQuery);