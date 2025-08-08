# File-Sharing-App-AWS
This application provides a simple and secure way to share files with multiple recipients via email. It leverages AWS S3 for file storage, AWS Lambda for sending email notifications, and a MySQL database for tracking uploads, email sends, clicks, and downloads.

Features:

  1. User authentication (basic username/password)
  2. Multiple file uploads
  3. Email notification to specified recipients with unique tracking links
  4. Download tracking
  5. Automatic deletion of files from S3 after all recipients have downloaded them
  
Prerequisites:

To run this application, you will need:

  1. Python 3.6 or higher: The application is written in Python and uses several libraries.
  2. Flask: A micro web framework for Python.
  3. Boto3: The AWS SDK for Python, used to interact with S3 and Lambda.
  4. PyMySQL: A pure Python MySQL client library.
  5. AWS Account: You will need an AWS account with access to:
      a. S3: For storing uploaded files. You'll need to create an S3 bucket.
      b. Lambda: To send email notifications. You'll need to create a Lambda function that sends emails (e.g., using SES). The provided code expects a Lambda function named file-sharing-send-email.
      c. IAM: To create IAM users with appropriate permissions to access S3 and invoke the Lambda function. You'll need the access key and secret access key.
  9. MySQL Database: A MySQL database to store upload and tracking information. You'll need the host, username, password, and database name. The database needs tables named uploads, email_tracking, clicks, and downloads with appropriate schemas to store the data.
  10. Email Sending Service: The Lambda function will need to use an email sending service like Amazon SES to send emails to recipients.
  11. Secure Key: A secret key for Flask sessions.

Setup and Configuration:

1. Install dependencies:
   pip install Flask boto3 pymysql
2. Configure AWS Credentials: Replace the placeholder values for aws_access_key_id and aws_secret_access_key in the boto3.client calls with your actual IAM user credentials.
3. Configure S3 Bucket: Replace bucket-name with the name of your S3 bucket.
4. Configure Database Connection: Replace the placeholder values for host, user, password, and database in the pymysql.connect call with your MySQL database credentials.
5. Configure AWS Lambda: Ensure you have a Lambda function named file-sharing-send-email set up to handle sending emails based on the payload structure sent by the Flask application.
6. Create Database Tables: Create the necessary tables in your MySQL database (uploads, email_tracking, clicks, downloads).
7. Set Flask Secret Key: Replace 'supersecretkey' with a strong, unique secret key for Flask sessions.
8. Create HTML Templates: You will need to create the following HTML template files in a templates directory in the same directory as your Python script:
9. login.html: For the login page.
10. upload.html: For the file upload page.
11. download.html: For the file download page. You will also need a static directory with a style.css file for styling.

Running the Application:

python your_app_file_name.py
The application will run on http://0.0.0.0:5001/.

Usage:

Access the application in your web browser.
Log in using the defined usernames and passwords.
Upload files and enter the email addresses of the recipients.
The recipients will receive emails with tracking links to download the files.
Once all recipients have downloaded the files, the files will be automatically deleted from S3.

Note:
This is a basic implementation and may require further security enhancements for production use.
The Lambda function for sending emails is not included in this code and needs to be implemented separately.
Consider using environment variables or a configuration file to manage sensitive credentials instead of hardcoding them in the script.
Implement more robust error handling and logging.
Add proper user management and access control for a production application.
