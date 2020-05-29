from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from flask.logging import create_logger
from functools import wraps
'''
mysqldb - helps in sql operations from flask app
wtforms - helps in form validations
passlib.hash - helps in encoding the password using hasing to store in database
create_logger - helps to log the details in console
flash- For flash messages
redirect and url_for - helps in redirection
request - helps to fetch request parameters such as methods, form details etc
Articles - customized module within project with json data of articles
wraps - to create a decorator, to restrict the url access when there is no active session
'''

app = Flask('__name__')
log = create_logger(app)

# config  Mysql
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'hbstudent'
app.config['MYSQL_PASSWORD'] = 'hbstudent'
app.config['MYSQL_DB'] = 'myflaskapp'
# by default cursorclass retun tuple, here we change explicitly
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# init mysql
mysql = MySQL(app)


Articles = Articles()


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/articles')
def articles():
    # create cursor
    cur = mysql.connection.cursor()
    # get articles
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = "No Articles Found"
        return render_template('articles.html', msg=msg)
    # close connection
    cur.close()


@app.route('/article/<string:id>')
def article(id):
    # create cursor
    cur = mysql.connection.cursor()
    # get articles
    cur.execute("SELECT * FROM articles WHERE id=%s", (id))

    articles = cur.fetchone()

    return render_template('article.html', articles=articles)


class RegisterForm(Form):
    '''
    source wtforms website, validating the form details using wtforms
    '''
    name = StringField('Name', validators=[
                       validators.input_required(), validators.Length(min=1, max=50)])
    username = StringField('Username', validators=[
                           validators.input_required(), validators.Length(min=4, max=25)])
    email = StringField('Email', validators=[
                        validators.input_required(), validators.Length(min=6, max=50)])
    password = PasswordField('Password', validators=[validators.DataRequired(
    ), validators.EqualTo('confirm', message='passwords do not match')])
    confirm = PasswordField('Confirm Password')


@app.route('/register', methods=['GET', 'POST'])
def register():
    '''
    This function used to validate registered form data using wtforms, and on successfull validations, insert details in mysql database
    '''
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        # read form values and store in mysql database
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # create a cursor
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(name, email, username , password) VALUES(%s, %s, %s, %s)",
                    (name, email, username, password))
        # commit to DB
        mysql.connection.commit()
        # close connection
        cur.close()

        flash('You are now registered and can login', 'success')
        return redirect(url_for('register'))
    return render_template('register.html', form=form)


# user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    '''
    This function used to validate username and password.
    on successfull login it starts the session and store username and logged_in to True
    '''
    if request.method == 'POST':
        # get forms fields
        username = request.form['username']
        password_candidate = request.form['password']

        # create cursor
        cur = mysql.connection.cursor()
        # Get user by username
        result = cur.execute(
            "SELECT * FROM users WHERE username= %s", [username])
        if result > 0:
            # get stored hash
            data = cur.fetchone()
            password = data['password']

            # compare the passwords
            if sha256_crypt.verify(password_candidate, password):
                # app.logger.info('Password matched')
                # once user login successfully create a session and store username in session
                session['logged_in'] = True
                session['username'] = username
                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))

            else:
                # app.logger.info('Password Not Matched')
                error = "Invalid login"
                return render_template('login.html', error=error)
            # close connection
            cur.close()
        else:
            # app.logger.info('No user')
            error = "username not found"
            return render_template('login.html', error=error)

    return render_template('login.html')


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, please login', 'danger')
            return redirect(url_for('login'))
    return wrap


@app.route('/dashboard')
@is_logged_in
def dashboard():
    # create cursor
    cur = mysql.connection.cursor()
    # get articles
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = "No Articles Found"
        return render_template('dashboard.html', msg=msg)
    # close connection
    cur.close()


class ArticleForm(Form):
    '''
    source wtforms website, validating the form details using wtforms
    '''
    title = StringField('Name', validators=[
        validators.input_required(), validators.Length(min=1, max=200)])
    body = TextAreaField('Username', validators=[
        validators.input_required(), validators.Length(min=30)])


@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # create a cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO articles(title,body,author) values(%s,%s,%s)",
                    (title, body, session['username']))
        # commit
        mysql.connection.commit()
        # close
        cur.close()
        flash('Article created', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_article.html', form=form)


@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # create cursor
    cur = mysql.connection.cursor()
    # get article by id
    cur.execute("SELECT * FROM articles WHERE id=%s", (id))
    article = cur.fetchone()

    # Get form
    form = ArticleForm(request.form)

    # populate articles from fields
    form.title.data = article['title']
    form.body.data = article['body']
    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # create a cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("UPDATE articles SET  title=%s, body=%s where id=%s",
                    (title, body, id))
        # commit
        mysql.connection.commit()
        # close
        cur.close()
        flash('Article Updated', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_article.html', form=form)


@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    # create cursor
    cur = mysql.connection.cursor()
    # delete articles
    cur.execute("DELETE FROM articles where id=%s", (id))
    # commit
    mysql.connection.commit()
    # close connection
    cur.close()
    flash('Article Deleted', 'success')
    return redirect(url_for('dashboard'))


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('you are now logged out', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(port=5050, debug=True)
