import json
import os

import boto3
from decouple import config
from flask import Blueprint, flash, jsonify, render_template, redirect, request, render_template_string, session, url_for
from flask_login import login_required, current_user, logout_user
import pandas as pd
import requests
from werkzeug.utils import secure_filename

from .auth import render_s3_template
from .extensions import lillith
from .forms import LoginForm, EditProfileForm, SwipeForm
from .photos import client, Photos
from .schema import UserSchema, Swipe
from .swipe_queue import SwipeQueue
from .tables import User, Swipe, db

main_bp = Blueprint(
    'main_bp',
    __name__,
    template_folder='templates',
    static_folder='static'
)

@main_bp.route('/home', methods = ['GET', 'POST'])
@login_required
def home():
    # if current_user.username + '_queue' not in session:
    #     session[current_user.username + '_queue'] = SwipeQueue(User.query.filter_by(username=current_user.username).first())

    #get user's swipe queue
    sq = session.get(current_user.username + '_queue')
    try:
        #retrieve swipee for template
        swipee = sq.next_user()
        #retrieve path to swipee's photos
        # s3_photos = Photos(swipee.username)
        # child_paths = s3_photos.get_paths_to_photos(swipee.username)
        #process user's swipe choice
        form = SwipeForm()
        if form.validate_on_submit():
            #User swipes on the swipee
            swipe_choice = form.swipe_choice.data
            #after backend logic, refresh the home page form
            return redirect(url_for('main_bp.home', form = form))
        # balance = lillith.functions.balanceOf().call({'from':swipee.address})
        #needs to loop through all profiles of user's gender preference within set radius
        #needs to display user's pictures and bio
        #needs to prompt yes or no (swipe)
        #needs to charge for swipe
        #needs to ask user to approve charge to wallet
        #when there are no more users in radius, needs to say "no more users!"
        return render_template('home.html', user=swipee, form=form)
    except:
        return render_template('no_more_users.html')

@main_bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    s3_photos = Photos(username)
    # child_paths = s3_photos.get_paths_to_photos(username)
    # return render_template('show_profile.html', user=user, child_paths=child_paths, s3_photos=s3_photos)
    return render_template('show_profile.html', user=user, s3_photos=s3_photos)

@main_bp.route('/user/<username>/edit', methods=['GET', 'POST'])
@login_required
def edit_profile(username):
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.bio = form.bio.data
        db.session.commit()
        #TODO update photo bucket on S3
        for uploaded_file in form.photos.data:
            if uploaded_file.filename != '':
                filename = secure_filename(uploaded_file.filename)
                file_ext = os.path.splitext(filename)[1]
                if file_ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif']:
                    return "Unfortnately, that image wasn't valid :(", 400
                local_photo_folder = os.path.join('s3', 'user', username)
                if not os.path.exists(local_photo_folder):
                    os.makedirs(local_photo_folder)
                uploaded_file.save(os.path.join(local_photo_folder, filename))
                client.upload_file(
                    os.path.join(local_photo_folder, filename),
                    config('BUCKET_NAME'),
                    os.path.join(local_photo_folder, filename),
                    ExtraArgs={'ACL': 'public-read'}
                )
        flash('Cool...your changes have been saved!')
        return redirect(url_for('main_bp.user', username=form.username.data))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.bio.data = current_user.bio
        #TODO display previous photos

    # return render_template('edit_profile.html', form=form)
    return render_template('edit_profile.html', form=form)

@main_bp.route('/user/<username>/matches')
@login_required
def matches(username = current_user):
    return render_template('matches.html', user=user)

@main_bp.route('/metamask-setup')
@login_required
def metamask_setup():
    pass

@main_bp.route('/reset')
def create_db():
    #reset db
    db.drop_all()
    db.create_all()
    users = []
    # users = [User(
    #     username='Tally', 
    #     password='test', 
    #     address='0xaB30CDAf3B2074B1C513bfA22598352dd4966497',
    #     left_swipes_given = 0,
    #     right_swipes_given = 0,
    #     matches = 0,
    #     bio = '',
    #     time_logged = 0,
    #     gender = '',
    #     gender_preference = ''
    #     )]
    with open('MOCK_DATA.json') as f:
        data = json.loads(f.read())
    for i in data:
        user = User(
            username=i['username'], 
            password=i['password'], 
            address=i['address'],
            left_swipes_given = i['left_swipes_given'],
            right_swipes_given = i['right_swipes_given'],
            matches = i['matches'],
            bio = i['bio'],
            time_logged = i['time_logged'],
            gender = i['gender'],
            gender_preference = i['gender_preference']
            )
        users.append(user)
    for user in users:
        user.set_password(user.password)
    db.session.add_all(users)
    db.session.commit()

    return 'DB created!'

@main_bp.route('/logout')
@login_required
def logout():
    '''user logout logic'''
    logout_user()
    return redirect(url_for('auth_bp.login'))

@main_bp.errorhandler(413)
def too_large(e):
    return "That photo was too large...", 413