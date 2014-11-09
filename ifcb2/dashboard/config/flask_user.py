
# Configure Flask-User module here
# for more information: http://pythonhosted.org/Flask-User/customization.html

# Settings                                      # Description
USER_APP_NAME              = 'IFCB Dashboard'   # Used by email templates

USER_AUTO_LOGIN                  = False

USER_AUTO_LOGIN_AFTER_CONFIRM    = USER_AUTO_LOGIN

USER_AUTO_LOGIN_AFTER_REGISTER   = USER_AUTO_LOGIN

USER_AUTO_LOGIN_AFTER_RESET_PASSWORD = USER_AUTO_LOGIN

USER_AUTO_LOGIN_AT_LOGIN         = USER_AUTO_LOGIN

USER_CONFIRM_EMAIL_EXPIRATION    = 2*24*3600   # Confirmation expiration in seconds
                                               # (2*24*3600 represents 2 days)

USER_PASSWORD_HASH               = 'bcrypt'    # Any passlib crypt algorithm

USER_PASSWORD_HASH_MODE   = 'Flask-Security'   # Set to 'Flask-Security' for
                                               # Flask-Security compatible hashing

SECURITY_PASSWORD_SALT = 'd*xkTKNcnka9RhcyL*UEW_cjWcD9^mVmUf*U_faZxNA@FF-7YLbSDFwLWG2uD$qY'
SECRET_KEY = SECURITY_PASSWORD_SALT
                                                # Only needed for
                                               # Flask-Security compatible hashing

USER_REQUIRE_INVITATION          = False       # Registration requires invitation
                                               # Not yet implemented
                                               # Requires USER_ENABLE_EMAIL=True

USER_RESET_PASSWORD_EXPIRATION   = 2*24*3600   # Reset password expiration in seconds
                                               # (2*24*3600 represents 2 days)

USER_SEND_PASSWORD_CHANGED_EMAIL = True        # Send registered email
                                               # Requires USER_ENABLE_EMAIL=True

USER_SEND_REGISTERED_EMAIL       = False       # Send registered email
                                               # Requires USER_ENABLE_EMAIL=True

USER_SEND_USERNAME_CHANGED_EMAIL = True        # Send registered email
                                               # Requires USER_ENABLE_EMAIL=True

# Features                     # Default   # Description
USER_ENABLE_CHANGE_PASSWORD    = False      # Allow users to change their password

USER_ENABLE_CHANGE_USERNAME    = False      # Allow users to change their username
                                           # Requires USER_ENABLE_USERNAME=True

USER_ENABLE_CONFIRM_EMAIL      = False      # Force users to confirm their email
                                           # Requires USER_ENABLE_EMAIL=True

USER_ENABLE_FORGOT_PASSWORD    = False      # Allow users to reset their passwords
                                           # Requires USER_ENABLE_EMAIL=True

USER_ENABLE_LOGIN_WITHOUT_CONFIRM = True  # Allow users to login without a
                                           # confirmed email address
                                           # Protect views using @confirm_email_required

USER_ENABLE_EMAIL              = False      # Register with Email
                                           # Requires USER_ENABLE_REGISTRATION=True

USER_ENABLE_MULTIPLE_EMAILS    = False     # Users may register multiple emails
                                           # Requires USER_ENABLE_EMAIL=True

USER_ENABLE_REGISTRATION       = False     # Allow new users to register

USER_ENABLE_RETYPE_PASSWORD    = True      # Prompt for `retype password` in:
                                           #   - registration form,
                                           #   - change password form, and
                                           #   - reset password forms.

USER_ENABLE_USERNAME           = False      # Register and Login with username

# URLs
USER_CHANGE_PASSWORD_URL      = '/sec/change-password'
USER_CHANGE_USERNAME_URL      = '/sec/change-username'
USER_CONFIRM_EMAIL_URL        = '/sec/confirm-email/<token>'
USER_EMAIL_ACTION_URL         = '/sec/email/<id>/<action>'     # v0.5.1 and up
USER_FORGOT_PASSWORD_URL      = '/sec/forgot-password'
USER_LOGIN_URL                = '/sec/login'
USER_LOGOUT_URL               = '/sec/logout'
USER_MANAGE_EMAILS_URL        = '/sec/manage-emails'
USER_REGISTER_URL             = '/sec/register'
USER_RESEND_CONFIRM_EMAIL_URL = '/sec/resend-confirm-email'    # v0.5.0 and up
USER_RESET_PASSWORD_URL       = '/sec/reset-password/<token>'

""" # Form template files
USER_CHANGE_PASSWORD_TEMPLATE           = 'flask_user/change_password.html'
USER_CHANGE_USERNAME_TEMPLATE           = 'flask_user/change_username.html'
USER_FORGOT_PASSWORD_TEMPLATE           = 'flask_user/forgot_password.html'
USER_LOGIN_TEMPLATE                     = 'flask_user/login.html'
USER_MANAGE_EMAILS_TEMPLATE             = 'flask_user/manage_emails.html'           # v0.5.1 and up
USER_REGISTER_TEMPLATE                  = 'flask_user/register.html'
USER_RESEND_CONFIRM_EMAIL_TEMPLATE      = 'flask_user/resend_confirm_email.html'    # v0.5.0 and up
USER_RESET_PASSWORD_TEMPLATE            = 'flask_user/reset_password.html'

# Place the Login form and the Register form on one page:
# Only works for Flask-User v0.4.9 and up
USER_LOGIN_TEMPLATE                     = 'flask_user/login_or_register.html'
USER_REGISTER_TEMPLATE                  = 'flask_user/login_or_register.html'

# Email template files                  # Defaults
USER_CONFIRM_EMAIL_EMAIL_TEMPLATE       = 'flask_user/emails/confirm_email'
USER_FORGOT_PASSWORD_EMAIL_TEMPLATE     = 'flask_user/emails/forgot_password'
USER_PASSWORD_CHANGED_EMAIL_TEMPLATE    = 'flask_user/emails/password_changed'
USER_REGISTERED_EMAIL_TEMPLATE          = 'flask_user/emails/registered'
USER_USERNAME_CHANGED_EMAIL_TEMPLATE    = 'flask_user/emails/username_changed'
"""
