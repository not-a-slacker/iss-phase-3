from flask import Flask, request, jsonify, redirect, url_for,send_from_directory
from flask import render_template
import mysql.connector
import hashlib
from werkzeug.utils import secure_filename
import os
import base64
from mutagen.mp3 import MP3
from mutagen.wavpack import WavPack
import numpy as np
import io 
import PIL.Image
from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_audioclips,vfx
import tempfile
from sqlalchemy import create_engine, Column, Integer, String, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import cv2
import numpy as np
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.mysql import BLOB
import os


current_user=-1
app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['DISPLAY_FOLDER'] = 'display'

engine = create_engine(os.environ["DATABASE_URL"])
Base = declarative_base()
Session = sessionmaker(bind=engine)






def delete_files_in_directory(directory_path):
    try:
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Deleted file: {filename}")
    except Exception as e:
        print(f"Error deleting files: {e}")



def get_image_format(image_data):
    # Extract the image format from the base64-encoded data
    return image_data[:image_data.find(b';')].decode('utf-8').split('/')[1]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

class UserDetails(Base):
    __tablename__ = 'user_details'

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(1000))
    user_name = Column(String(1000))
    email = Column(String(1000))
    password = Column(String(1000))

class Image(Base):
    __tablename__ = 'images'

    image_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    image = Column(BLOB)
    image_metadata = Column(String(1000))
    extension = Column(String(20))


class Audio(Base):
    __tablename__ = 'audio'

    audio_id = Column(Integer, primary_key=True, autoincrement=True)
    audio_data = Column(BLOB)
    audio_metadata = Column(String(1000))



def create_tables():
    Base.metadata.create_all(engine)
def insert_data(name1, username1, email1, password1):
    session = Session()
    try:
        user = UserDetails(name=name1, user_name=username1, email=email1, password=password1)
        session.add(user)
        session.commit()
        print("Data inserted successfully!")
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()
        print("Session closed")



def search_for_JUST_username(username_user):
    session = Session()
    try:
        # Query the user_details table for a specific username
        user = session.query(UserDetails).filter(UserDetails.user_name == username_user).first()
        
        if user:
            return user.user_id
        else:
            return 0
    except Exception as e:
        print(f"Error: {e}")
        return 0
    finally:
        session.close()
        print("Session closed")


def search_for_user(username_user, password_user):
    try:
        session = Session()

        user = session.query(UserDetails).filter_by(user_name=username_user, password=password_user).first()

        if user:
            user_id = user.user_id
            session.close()
            print("MySQL connection closed")
            return user_id
        else:
            session.close()
            print("MySQL connection closed")
            return 0
    
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return 0

def get_user_details(user_id):
    try:
        session = Session()

        user = session.query(UserDetails).filter_by(user_id=user_id).first()

        if user:
            user_details = {
                'name': user.name,
                'user_name': user.user_name,
                'email': user.email,
                'password': user.password,
                'user_id': user.user_id
            }
            session.close()
            print("MySQL connection closed")
            return user_details
        else:
            session.close()
            print("MySQL connection closed")
            return None

    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return None
def save_to_database(file_path, user_id, extension):
    try:
        session = Session()

        with open(file_path, 'rb') as file:
            image_data = file.read()

        # Create an Image object and add it to the session
        image = Image(image=image_data, user_id=user_id, extension=extension)
        session.add(image)
        session.commit()

    except Exception as e:
        print(f"Error: {e}")
        session.rollback()  # Rollback the transaction in case of error

    finally:
        session.close()


def get_audio():
    try:
        session = Session()

        # Retrieve audio data from the database
        audios = session.query(Audio.audio_data).all()

        audio_data_list = []
        for audio_data in audios:
            # Convert audio_data to base64 for embedding in HTML
            encoded_audio = base64.b64encode(audio_data[0]).decode('utf-8')
            audio_data_list.append(f"data:audio/mp3;base64,{encoded_audio}")

        return audio_data_list

    except Exception as e:
        print(f"Error: {e}")

    finally:
        session.close()
def get_images(user_id):
    try:
        session = Session()

        # Retrieve images for the specified user_id from the database
        images = session.query(Image.image, Image.extension).filter_by(user_id=user_id).all()

        image_data_list = []
        for image_data, image_extension in images:
            # Convert image_data to base64 for embedding in HTML
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            image_data_list.append(f"data:image/{image_extension};base64,{encoded_image}")

        return image_data_list

    except Exception as e:
        print(f"Error: {e}")

    finally:
        session.close()








@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html',target="_self")

@app.route('/login',methods=['GET','POST'])
def login():
    
    if request.method=='POST':
        username_login=request.form['username']
        password_login=request.form['password']
        hashed_password_login = hashlib.sha256(password_login.encode()).hexdigest()
        a=search_for_user(username_login,hashed_password_login)
        if a==0:
            return render_template('login.html', login_failed=True)
        else:
            global current_user
            current_user=a
            return redirect(url_for('home',user_id=a))

        
    return render_template('login.html',target="_self")

@app.route('/signup',methods=['GET','POST'])
def signup():
    
    if request.method=='POST':
        username_user=request.form['username']
        name_user=request.form['name']
        email_user=request.form['email']
        password_user=request.form['password']
        confirmed_password_user=request.form['confirm-password']
        a=search_for_JUST_username(username_user)
        print(a)
        if(a!=0 and password_user!=confirmed_password_user):
            return render_template('signup.html', password_mismatch=True,user_found=True)
        elif(a!=0):
            return render_template('signup.html', password_mismatch=False,user_found=True)
        elif(password_user!=confirmed_password_user):
            return render_template('signup.html', password_mismatch=True,user_found=False)
        else:
            hashed_password = hashlib.sha256(password_user.encode()).hexdigest()
            insert_data(name_user, username_user, email_user, hashed_password)
            return redirect(url_for('login'))


    return render_template('signup.html', password_mismatch=False,user_found=False,target="_self")

@app.route('/home/user/<int:user_id>',methods=['GET','POST'])
def home(user_id):
    if request.method=='POST':
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            image_extension = file.filename.rsplit('.', 1)[1].lower()

            # Save the file path to the database along with metadata
            save_to_database(file_path,user_id,image_extension)
            

            return jsonify({"status": "success"})

        return jsonify({"status": "failed"})
    else:
        image_data_list = get_images(user_id)
        row=get_user_details(user_id)
        # Render HTML to display images
        return render_template('home.html', user_id=user_id,image_data_list=image_data_list,row=row )
    


            

            




@app.route('/admin')
def admin():
    return render_template('admin.html',target="_self")

@app.route('/videopage/user')
def videopage():
    global current_user
    user_id=current_user
    image_data_list = get_images(user_id)
    audio_data_list=get_audio()
    print(len(image_data_list))
    return render_template('videopage.html',user_id=user_id,image_data_list=image_data_list,audio_data_list=audio_data_list)


@app.route('/create_video', methods=['POST'])
def create_video():
    data = request.get_json()
    images = data['images']  
    fps = 1/int(data['fps'])
    width = int(data['width'])
    height = int(data['height'])
    audios=data['audios']
    quality_val=int(data['quality'])

    try:

        video_clips = []

        # Iterate through the image URLs
        for image_url in images:
            # Decode the base64 encoded image
            image_data = base64.b64decode(image_url.split(',')[1])

            # Convert the image data to PIL Image object
            img = PIL.Image.open(io.BytesIO(image_data))

            # Ensure image is in RGB mode for compatibility
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Resize the image to match the video dimensions
            img = img.resize((width, height), resample=PIL.Image.BICUBIC)

            # Compress the image to a desired quality
            
            img_io = io.BytesIO()
            img.save(img_io, 'JPEG', quality=quality_val)
            img = PIL.Image.open(img_io)
            # Convert PIL Image to numpy array
            img_array = np.array(img)

            # Append the image array to the video clips list
            video_clips.append(img_array)

        # Create ImageSequenceClip from the list of image arrays
        if video_clips:
            final_clip = ImageSequenceClip(video_clips, fps=fps)
        else:
            print("No valid images provided.")
            return jsonify({"status": "failed", "message": "No valid images provided."})

       
        if audios != []:
            audio_clips = []

            for audio in audios:
                # Decode the base64 encoded audio
                audio_data = base64.b64decode(audio['src'].split(',')[1])

                # Create a temporary file and write the decoded audio data to it
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
                    temp_audio_file.write(audio_data)
                    temp_audio_path = temp_audio_file.name

                # Load the audio clip from the temporary file
                audio_clip = AudioFileClip(temp_audio_path)

                # Append the audio clip to the audio clips list
                audio_clips.append(audio_clip)

            # Concatenate all audio clips into a single long audio clip
            concatenated_audio = concatenate_audioclips(audio_clips)

            # Loop the concatenated audio until it matches the video duration
            looped_audio = concatenated_audio.fx(vfx.loop, duration=final_clip.duration)

            # Add the looped audio clip to the final video clip
            final_clip = final_clip.set_audio(looped_audio)
        
        # Define the output path for the final video
        output_path = os.path.join('static', 'output_video.mp4')

        # Write the final video clip to the output path using H.264 codec
        final_clip.write_videofile(output_path, codec='libx264')

        return jsonify({"status": "success", "output": output_path})

    except Exception as e:
        print(f"Error creating video: {e}")
        return jsonify({"status": "failed"})
    
    
if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
