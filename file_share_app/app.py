from flask import Flask, request, render_template, redirect, flash, session, url_for
import boto3, json
import pymysql
import os, time
from uuid import uuid4
from werkzeug.utils import secure_filename
from flask import Response, stream_with_context


s3 = boto3.client(
    's3',
    aws_access_key_id='IAM-access-key',
    aws_secret_access_key='IAM-secret-access-key',
    region_name='us-east-2'  
)
S3_BUCKET = 'bucket-name'

db = pymysql.connect(
    host='RDS-Endpoint',
    user='username',
    password='password',
    database='DB-name'
)

lambda_client = boto3.client(
    'lambda',
    aws_access_key_id='IAM-access-key',
    aws_secret_access_key='IAM-secret-access-key',
    region_name='us-east-2'
)

app = Flask(__name__)
app.secret_key = 'supersecretkey'  


USERS = {
    'user1': 'password1',
    'user2': 'password2',
}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in USERS and USERS[username] == password:
            session['username'] = username
            flash(f'Welcome, {username}!')
            return redirect(url_for('upload_file'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.')
    return redirect(url_for('login'))



@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if 'username' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            flash('No files selected.')
            return redirect(request.url)

        emails = [request.form.get(f'email{i}') for i in range(1, 6)]
        emails = [e for e in emails if e]

        if not emails:
            flash('Please enter at least one email.')
            return redirect(request.url)
        
        username = session['username']
        uploaded_filenames = []
        s3_keys = []

        file_id = str(uuid4())  

        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                s3_key = f"{file_id}/{filename}"
                try:

                    s3.upload_fileobj(file, S3_BUCKET, s3_key)

                    with db.cursor() as cursor:
                        cursor.execute(
                            "insert into uploads (username, filename) VALUES (%s, %s)",
                            (username, filename)
                        )
                    
                    with db.cursor() as cursor:
                        for email in emails:
                            cursor.execute(
                                "insert into email_tracking (file_id, email, file_key) VALUES (%s, %s, %s)",
                                (file_id, email, s3_key)
                            )

                    db.commit()
                    uploaded_filenames.append(filename)
                    s3_keys.append(s3_key)

                except Exception as e:
                    flash(f"Failed to upload {file.filename}: {e}")

        if s3_keys and emails:
            lambda_payload = {
                'bucket': S3_BUCKET,
                'keys': s3_keys,
                'emails': emails,
                'file_id': file_id,
                'base_url': request.url_root.rstrip('/')
            }
            try:
                response = lambda_client.invoke(
                    FunctionName='file-sharing-send-email',
                    InvocationType='Event',
                    Payload=json.dumps(lambda_payload)
                )
            except Exception as e:
                flash(f"Failed to send emails: {e}")

        if uploaded_filenames:
            flash(f"Uploaded: {', '.join(uploaded_filenames)}")
        return redirect('/')

    return render_template('upload.html')


@app.route('/track')
def track_file():
    file_id = request.args.get('file_id')
    email = request.args.get('email')

    if not file_id or not email:
        return "Invalid tracking link.", 400

    try:
        with db.cursor() as cursor:
            cursor.execute("select 1 from clicks where file_id=%s and email=%s", (file_id, email))
            if not cursor.fetchone():
                cursor.execute("insert into clicks (file_id, email) values (%s, %s)", (file_id, email))

            cursor.execute("select file_key from email_tracking where file_id=%s and email=%s", (file_id, email))
            keys = [row[0] for row in cursor.fetchall()]

            download_links = []
            for key in keys:
                filename = key.split('/')[-1]
                url = url_for('download_file', file_key=key, file_id=file_id, email=email, _external=True)
                download_links.append({'name': filename, 'url': url})

            db.commit()

        return render_template('download.html', download_links=download_links)

    except Exception as e:
        return f"Error: {str(e)}", 500


@app.route('/download')
def download_file():
    file_key = request.args.get('file_key')
    file_id = request.args.get('file_id')
    email = request.args.get('email')

    if not file_key or not file_id or not email:
        return "Invalid download link.", 400

    try:
        s3_object = s3.get_object(Bucket=S3_BUCKET, Key=file_key)
        file_size = s3_object['ContentLength']
        content_type = s3_object.get('ContentType', 'application/octet-stream')

        def generate():
            for chunk in s3_object['Body'].iter_chunks(chunk_size=8192):
                yield chunk


        response = Response(stream_with_context(generate()), mimetype=content_type)
        response.headers.set('Content-Disposition', f'attachment; filename="{file_key.split("/")[-1]}"')
        response.headers.set('Content-Length', file_size)

        @response.call_on_close
        def after_download():
            with db.cursor() as cursor:
                cursor.execute("""
                    select 1 from downloads where file_id=%s and email=%s AND file_key=%s
                """, (file_id, email, file_key))
                if not cursor.fetchone():
                    cursor.execute("""
                        insert into downloads (file_id, email, file_key) VALUES (%s, %s, %s)
                    """, (file_id, email, file_key))

                cursor.execute("""select count(*) from email_tracking where file_id=%s""", (file_id,))
                expected = cursor.fetchone()[0]

                cursor.execute("""select count(*) from downloads where file_id=%s""", (file_id,))
                actual = cursor.fetchone()[0]
                print("actual:"+str(actual)+"\nexpected:"+str(expected))
                if actual >= expected:
                    cursor.execute("""select distinct file_key from email_tracking where file_id=%s""", (file_id,))
                    keys_to_delete = cursor.fetchall()
                    for row in keys_to_delete:
                        s3.delete_object(Bucket=S3_BUCKET, Key=row[0])
                    print('files deleted')

                db.commit()

        return response
    
    except Exception as e:
        if e.response['Error']['Code'] == '404' or e.response['Error']['Code'] == 'NoSuchKey':
            return render_template("download.html", error="This file has already been deleted after all recipients downloaded it.")
        else:
            return render_template("download.html", error=f"Unexpected error: {str(e)}")


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001)
