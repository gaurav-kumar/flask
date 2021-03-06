import functools
from logging import error

# url_for() generates the URL for the login view based on its name.
# The url_for() function generates the URL to a view based on a name and arguments.
# The name associated with a view is also called the endpoint, and by default it’s the same as the name of the view function.

# session is a dict that stores data across requests.
# The data is stored in a cookie that is sent to the browser, and the browser then sends it back with subsequent requests.
# Flask securely signs the data so that it can’t be tampered with.
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from myblog.db import get_db


# A Blueprint is a way to organize a group of related views and other code. Rather than registering views and other code directly with an application, they are registered with a blueprint.
# Then the blueprint is registered with the application when it is available in the factory function.
# The blueprint needs to know where it’s defined, so __name__ is passed as the second argument.
# The url_prefix will be prepended to all the URLs associated with the blueprint.
bp = Blueprint('auth', __name__, url_prefix='/auth')


# @bp.route associates the URL /register with the register view function. When Flask receives a request to /auth/register, it will call the register view and use the return value as the respons
@bp.route('/register', methods=('GET', 'POST'))
def register():
    # If the user submitted the form, request.method will be 'POST'. In this case, start validating the input.
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        # db.execute() takes a SQL query with ? placeholders for any user input, and a tuple of values to replace the placeholders with.
        # The database library will take care of escaping the values so you are not vulnerable to a SQL injection attack.
        # fetchone() returns one row from the query. If the query returned no results, it returns None.
        # fetchall() is used to return a list of all results.
        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif db.execute('SELECT id FROM user WHERE username = ?', (username,)).fetchone() is not None:
            error = f'User {username} is already registered.'

        if error is None:
            # generate_password_hash() is used to securely hash the password, and that hash is stored.
            db.execute('INSERT INTO user (username, password) VALUES (?, ?)',
                       (username, generate_password_hash(password)))
            db.commit()

            # After storing the user, they are redirected to the login page.
            # This is preferable to writing the URL directly as it allows you to change the URL later without changing all code that links to it. redirect() generates a redirect response to the generated URL.
            # When using a blueprint, the name of the blueprint is prepended to the name of the function, so the endpoint for the login function you wrote below is 'auth.login' because you added it to the 'auth' blueprint.
            return redirect(url_for('auth.login'))

        # If validation fails, the error is shown to the user. flash() stores messages that can be retrieved when rendering the template.
        flash(error)

    # When the user initially navigates to auth/register, or there was a validation error, an HTML page with the registration form should be shown.
    # render_template() will render a template containing the HTML
    return render_template('auth/register.html')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute('SELECT * FROM user WHERE username=?',
                          (username,)).fetchone()

        # check_password_hash() hashes the submitted password in the same way as the stored hash and securely compares them. If they match, the password is valid.
        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            # When validation succeeds, the user’s id is stored in a new session.
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')


# bp.before_app_request() registers a function that runs before the view function, no matter what URL is requested.
@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute('SELECT * FROM user WHERE id=?', (user_id,)).fetchone()


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# This decorator returns a new view function that wraps the original view it’s applied to.
# The new function checks if a user is loaded and redirects to the login page otherwise.
# If a user is loaded the original view is called and continues normally.
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view
