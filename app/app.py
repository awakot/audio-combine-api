from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
import boto3
import os
import logging
from datetime import datetime
import time
from pydub import AudioSegment


app = Flask(__name__)
app.config["DEBUG"] = True
bucket = 'zappa-2j5f0hhy0'

UPLOAD_DIRECTORY = "/tmp"
ALLOWED_EXTENSIONS = {'mp3'}


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_companies', methods=['GET'])
def get_companies():
    return jsonify({'result': ['bytedance', 'grab']})


@app.route('/upload', methods=['POST'])
def upload_audio():
    # request.args.to_dict() get parameters
    # records = request.data
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No selected file'})
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'})
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            app.logger.info('load file {}'.format(filename))
            filepath = os.path.join(UPLOAD_DIRECTORY, filename)
            file.save(filepath)
            app.logger.info('file saved to {}'.format(filepath))
            s3key = uploadTos3(filepath)
            return jsonify({'s3_key': s3key})
        else:
            return jsonify({'error': 'File format wrong, allowed formats are {}'.format(ALLOWED_EXTENSIONS)})

@app.route('/mix', methods=['GET'])
def mix_audio():
    # request.args.to_dict() get parameters
    # records = request.data
    if request.method == 'GET':
        print(request)
        file1name = request.args.get('file1')
        file2name = request.args.get('file2')
        s3 = boto3.client('s3')
        s3.download_file(bucket, 'mp3/' + file1name, 'tmp/' + file1name)
        s3.download_file(bucket, 'mp3/' + file2name, 'tmp/' + file2name)
        mix_audio('tmp/'+file1name,'tmp/'+file2name)
        s3key = uploadTos3('tmp/output.mp3')
        return jsonify({'s3_key': s3key})


def uploadTos3(filepath):
    date_utc = datetime.utcfromtimestamp(int(time.time()))
    appendix = str(date_utc.hour).zfill(2) + str(date_utc.minute).zfill(2) + str(date_utc.second).zfill(2)
    key = 'mp3/' + 'audio_' + appendix + '.mp3'
    app.logger.info('s3 saved file key {}'.format(key))
    s3 = boto3.client('s3')
    with open(filepath, "rb") as f:
        s3.upload_fileobj(f, bucket, key)
    return key

def mix_audio(file1, file2):
    sound1 = AudioSegment.from_file(file1, format="mp3")
    sound2 = AudioSegment.from_file(file2, format="mp3")

    # sound1 6 dB louder
    louder = sound1 + 6

    # Overlay sound2 over sound1 at position 0  (use louder instead of sound1 to use the louder version)
    overlay = sound1.overlay(sound2, position=0)

    # simple export
    return overlay.export("tmp/output.mp3", format="mp3")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def remove_file(filepath):
    os.remove(filepath)
    app.logger.info('removed file {}'.format(filepath))

app.run()
