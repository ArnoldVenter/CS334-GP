from .models import User, get_todays_recent_questions, get_question, get_answers, do_search
from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory

import os, logging
from werkzeug.utils import secure_filename


app = Flask(__name__)
file_handler = logging.FileHandler('server.log')
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

PROJECT_HOME = os.path.dirname(os.path.realpath(__file__))
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def create_new_folder(local_dir):
    """Creates a folder if it does not exist already."""
    newpath = local_dir
    if not os.path.exists(newpath):
        os.makedirs(newpath)
    return newpath

@app.route('/upload_file/<username>', methods=['GET', 'POST'])
def upload_file(username):
    """Handles image uploads for profile pics. Modified from example given by FLASK.
    Files are saved as <username>.<original type>, eg user.jpg. This ensures there is
    always only one image per user."""
    if request.method == 'POST' and request.files['file']:
    	img = request.files['file']
    	create_new_folder(app.config['UPLOAD_FOLDER'])
    	saved_path =PROJECT_HOME + "/" + os.path.join(app.config['UPLOAD_FOLDER'], username + "." + img.filename.split(".")[-1])
    	img.save(saved_path)
    	User(username).change_pic_url(username + "." + img.filename.split(".")[-1])
    	return redirect(url_for('index'))
    else:
        return render_template('upload_file.html')



@app.route('/')
def index():
    """Gets all the recent questions, returns with index template."""
    questions = get_todays_recent_questions()
    return render_template('index.html', questions=questions)

@app.route('/register', methods=['GET','POST'])
def register():
    """Handles new registrations. Username length > 1; password length > 5;
    TODO: Add another password entry to see if both match up."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if len(username) < 1:
            flash('Your username must be at least one character.')
        elif len(password) < 5:
            flash('Your password must be at least 5 characters.')
        elif not User(username).register(password):
            flash('A user with that username already exists.')
        else:
            session['username'] = username
            flash('Logged in.')
            return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles the log in screen."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not User(username).verify_password(password):
            flash('Invalid login.')
        else:
            session['username'] = username
            flash('Logged in.')
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Closes user session, returns index."""
    session.pop('username', None)
    flash('Logged out.')
    return redirect(url_for('index'))

@app.route('/add_post', methods=['POST'])
def add_question():
    """Will always be a POST. Gets the question data, adds it to database."""
    title = request.form['title']
    text = request.form['text']
    art = request.form.get('art')
    exercise = request.form.get('exercise')
    food = request.form.get('food')
    hobbies = request.form.get('hobbies')
    lifestyle = request.form.get('lifestyle')
    music = request.form.get('music')
    nature = request.form.get('nature')
    psychology = request.form.get('psychology')
    relationships = request.form.get('relationships')
    technology = request.form.get('technology')
    tags_included = ""
    # tags seperated by " ". We can do this since we have predefined the tags and no spaces will creep in.
    if(art):
        tags_included = tags_included + "art "
    if(exercise):
        tags_included = tags_included + "exercise "
    if(food):
        tags_included = tags_included + "food "
    if(hobbies):
        tags_included = tags_included + "hobbies "
    if(lifestyle):
        tags_included = tags_included + "lifestyle "
    if(music):
        tags_included = tags_included + "music "
    if(nature):
        tags_included = tags_included + "nature "
    if(psychology):
        tags_included = tags_included + "psychology "
    if(relationships):
        tags_included = tags_included + "relationships "
    if(technology):
        tags_included = tags_included + "technology "
    # remove trailing whitespace
    tags_included = tags_included.rstrip()
    if not title:
        flash('You must give your question a title.')
    elif not tags_included:
        flash('You must give your question at least one tag.')
    elif not text:
        flash('You must give your question a text body.')
    else:
        User(session['username']).add_question(title, tags_included, text)
    return redirect(url_for('index'))

@app.route('/bookmark_question/<question_id>')
def bookmark_question(question_id):
    """Adds a bookmark if a user if logged in."""
    username = session.get('username')
    if not username:
        flash('You must be logged in to bookmark a question.')
        return redirect(url_for('login'))
    User(username).bookmark_question(question_id)
    flash('Bookmarked question.')
    return redirect(request.referrer)

@app.route('/upvote_answer/<answer_id>')
def upvote_answer(answer_id):
    """Upvotes an answer if a user is logged in."""
    username = session.get('username')
    if not username:
        flash('You must be logged in to upvote an answer.')
        return redirect(url_for('login'))
    User(username).upvote_answer(answer_id)
    flash('Upvoted.')
    return redirect(request.referrer)

@app.route('/profile/<username>')
def profile(username):
    """Gets data needed and displays a users profile."""
    logged_in_username = session.get('username')
    user_being_viewed_username = username
    user_being_viewed = User(user_being_viewed_username)
    questions = user_being_viewed.get_recent_questions()
    userbio = user_being_viewed.get_bio()
    recommend_users = []
    common = []
    profile_pic_url = "/static/uploads/" + user_being_viewed.get_pic_url()
    if logged_in_username:
        logged_in_user = User(logged_in_username)
        if logged_in_user.username == user_being_viewed.username:
            recommend_users = logged_in_user.suggest_follow()
        else:
            common = logged_in_user.get_commonality_of_user(user_being_viewed)
    return render_template(
        'profile.html',
        username=username,
        pic_url = profile_pic_url,
        questions=questions,
        recommend_users=recommend_users,
        common=common,
        userbio=userbio
    )

@app.route('/change_user_tags/<username>', methods=['GET','POST'])
def change_user_tags(username):
    """Removes all current tags, adds selected ones."""
    if request.method == 'POST':
        art = request.form.get('art')
        exercise = request.form.get('exercise')
        food = request.form.get('food')
        hobbies = request.form.get('hobbies')
        lifestyle = request.form.get('lifestyle')
        music = request.form.get('music')
        nature = request.form.get('nature')
        psychology = request.form.get('psychology')
        relationships = request.form.get('relationships')
        technology = request.form.get('technology')
        tags_included = ""
        tags_excluded = "" #NOTE: not used, but hassle to remove from function calls.
        # tags seperated by " ". We can do this since we have predefined the tags and no spaces will creep in.
        if(art):
            tags_included = tags_included + "art "
        if(exercise):
            tags_included = tags_included + "exercise "
        if(food):
            tags_included = tags_included + "food "
        if(hobbies):
            tags_included = tags_included + "hobbies "
        if(lifestyle):
            tags_included = tags_included + "lifestyle "
        if(music):
            tags_included = tags_included + "music "
        if(nature):
            tags_included = tags_included + "nature "
        if(psychology):
            tags_included = tags_included + "psychology "
        if(relationships):
            tags_included = tags_included + "relationships "
        if(technology):
            tags_included = tags_included + "technology "
        # remove trailing whitespace
        tags_included = tags_included.rstrip()
        tags_excluded = tags_excluded.rstrip()
        #print("included: " + tags_included)
        #print("excluded: " + tags_excluded)
        user = User(username)
        user.removeTags(tags_excluded)
        user.addTags(tags_included)
        return redirect(url_for('index'))
    return render_template(
        'change_user_tags.html'
        )

@app.route('/change_password/<username>', methods=['GET','POST'])
def change_password(username):
    """Changes a user's password."""
    if request.method == 'POST':
        old_password = request.form['old_pass']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        print("OLD: " + old_password)
        print("NEW: " + new_password)
        print("CONFIRM: " + confirm_password)
        if not User(username).verify_password(old_password):
            flash('Invalid old password.')
        elif (new_password != confirm_password):
            flash('New passwords do not match.')
        else:
            user = User(username)
            user.change_password(new_password)
            return redirect(url_for('index'))
    return render_template(
        'change_password.html'
        )

@app.route('/change_bio/<username>', methods=['GET','POST'])
def change_bio(username):
    """Changes a user's bio."""
    if request.method == 'POST':
        bio = request.form['bio']
        user = User(username)
        user.change_bio(bio)
        return redirect(url_for('index'))
    return render_template(
        'change_bio.html'
        )

@app.route('/show_question/<question_id>', methods=['GET','POST'])
def show_question(question_id):
    """Gets a question and all related answers and displays them."""
    session['question_id'] = question_id
    questions = get_question(question_id)
    answers = get_answers(question_id)
    return render_template('show_question.html', questions=questions, answers=answers)


@app.route('/add_answer', methods=['POST'])
def add_answer():
    """Adds an answer to a question."""
    text = request.form['text']
    if not text:
        flash('You must give your answer a text body.')
    else:
        User(session['username']).add_answer(session['question_id'], text)
    return redirect(request.referrer)


@app.route('/show_bookmarked/<username>', methods=['GET','POST'])
def show_bookmarked(username):
    """Gets all the user's bookmarked questions."""
    questions = User(username).get_bookmarks()
    return render_template('show_bookmarked.html', questions=questions)

@app.route('/timeline/<username>', methods=['GET','POST'])
def timeline(username):
    """Gets all the users followed questions, arranged according to most
    recently modified."""
    questions = User(username).get_timeline()
    return render_template('timeline.html', questions=questions)

@app.route('/voteline/<username>', methods=['GET','POST'])
def voteline(username):
    """Gets all the user's followed questions, arranged according to
    most upvotes."""
    questions = User(username).get_voteline()
    return render_template('voteline.html', questions=questions)


@app.route('/feedline/<username>', methods=['GET','POST'])
def feedline(username):
    """Gets all the user's followed questions, arranged according to
    most upvotes."""
    questions = User(username).get_following_feed()
    return render_template('voteline.html', questions=questions)



@app.route('/user_search/<username>', methods=['GET','POST'])
def user_search(username):
    """Displays the search results of a search for a user."""
    usernm = request.form['user']
    user = do_search(usernm)
    return render_template('user_search.html', username=username, user=user)

@app.route('/follow_user/<username>')
def follow_user(username):
    """Handles the follow procedure when this user wants to follow another."""
    username_me = session['username']
    username_him = username
    if not username_me:
        flash('You must be logged in to follow a user.')
        return redirect(url_for('login'))
    User(username_me).follow_user(username_him)
    flash('Followed.')
    return redirect(request.referrer)


@app.route('/open_follow/<username>')
def open_follow(username):
    """Gets the list of followed questions, and displays it to those who follow
    this user and is viewing this user's profile."""
    username_me = session['username']
    username_him = username
    user=User(username_me)
    if not username_me:
        flash('You must be logged in to follow a user.')
        return redirect(url_for('login'))
    if(user.test_follow(username_him) == True):
        User(username_me).follow_user(username_him)
        questions = User(username).get_timeline()
        return render_template('open_follow.html', questions=questions)
    flash('You must follow this user to see this data.')
    return redirect(request.referrer)

def allowed_file(filename):
    """Note used anymore."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
