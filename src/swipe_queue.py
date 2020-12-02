import datetime
import random

from flask import render_template, redirect, flash

from .tables import User, Swipe, db

class SwipeQueue:
    
    def __init__(self, user):
        self.user = user
        self.queue = User.query.all().remove(user)

    # TODO might need to move this to a different worker
    def add_user_to_queue(self, user):
        random.shuffle(self.queue)
        self.queue.append(user)
    
    def swipe(self):

        key = self.process_key_input()

        if key == 'p':
            return redirect('/profile')

        #if the user has no more people in the radius, relay message to user with template
        if not self.queue:
            return redirect('/no-more-users')
        #else, show next user
        else:
            next_user = self.queue.pop(0)
            #if user swipes left
            if key == 'left':
            #   append to swipe database
                swipe = Swipe(timestamp = datetime.datetime.now(),
                            decision = False,
                            front_user = self.user.username,
                            back_user = next_user.username,
                            match = False)
                db.session.add(swipe)
                db.session.commit()
        #elif user swipes right
            if key == 'right':
                # query db to see if our back user (note: for them, theyre the front user) reciprocates
                back_user_status = Swipe.query.filter_by(front_user=next_user.username,
                                                         back_user=self.user.username).first()
                #if the back user hasn't swiped on you yet
                if not back_user_status:
                    swipe = Swipe(timestamp = datetime.datetime.now(),
                            decision = True,
                            front_user = self.user,
                            back_user = next_user.username,
                            match = False)
                #Else if the back swiped left on you, no match
                elif back_user_status.decision == False:
                    swipe = Swipe(timestamp = datetime.datetime.now(),
                            decision = True,
                            front_user = self.user,
                            back_user = next_user.username,
                            match = False)
                #else, there's a match!
                else:
        #           alert front users
                    flash('New match! Take some coins!')
                    #alert back user TODO
        #           disperse funds to both users TODO web3
                    #update records
                    swipe = Swipe(timestamp = datetime.datetime.now(),
                            decision = True,
                            front_user = self.user,
                            back_user = next_user.username,
                            match = True)
                    #increment match total in User db
                    front_user = self.user
                    back_user = (User.query
                        .filter_by(User.username==next_user.username)
                        .first())
                    front_user.matches += 1
                    front_user.right_swipes +=1 
                    back_user.matches += 1
                    back_user.right_swipes +=1
                    db.session.commit() 
        #   show next user
            self.swipe()
    def process_key_input(self):
        if keyboard.is_pressed('p'):
            return 'p'
        elif keyboard.is_pressed('left'):
            return 'left'
        elif keyboard.is_pressed('right'):
            return 'right'
        else:
            self.process_key_input()
            

# user = self.queue.pop(0)
