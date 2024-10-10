import boto3
import smtplib
from email.mime.text import MIMEText

# Configuration
project_name = 'node_build_app'
region_name = 'us-east-1'
ses_sender_email = 'vikash.indoqubix@gmail.com' 
recipient_email = 'vikash.kumar@indoqubix.com'  # Replace with the recipient's email
smtp_username = 'vikash.kumar@indoqubix.com'  # Your Gmail address
smtp_password = 'rxhs asuc ygnt rdqv'  # Your Gmail app password

def get_latest_build_id(project_name):
    client = boto3.client('codebuild', region_name=region_name)
    response = client.list_builds_for_project(projectName=project_name, sortOrder='DESCENDING')
    return response['ids'][0] if response['ids'] else None

def get_build_details(build_id):
    client = boto3.client('codebuild', region_name=region_name)
    response = client.batch_get_builds(ids=[build_id])
    return response['builds'][0] if response['builds'] else None

def get_logs(log_group_name, log_stream_name):
    client = boto3.client('logs', region_name=region_name)
    response = client.get_log_events(logGroupName=log_group_name, logStreamName=log_stream_name, limit=100)
    return [event['message'] for event in response['events']]

def save_logs_to_file(logs, filename='build_logs.txt'):
    with open(filename, 'w') as f:
        for log in logs:
            f.write(f"{log}\n")

def send_email(logs):
    msg = MIMEText("\n".join(logs))
    msg['Subject'] = f'Build Failure Logs for {project_name}'
    msg['From'] = ses_sender_email
    msg['To'] = recipient_email

    with smtplib.SMTP('smtp.gmail.com', 587) as server:  # Gmail SMTP server
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(ses_sender_email, [recipient_email], msg.as_string())

def main():
    latest_build_id = get_latest_build_id(project_name)
    if not latest_build_id:
        print("No builds found for the project.")
        return
    
    build_details = get_build_details(latest_build_id)
    if build_details['buildStatus'] == 'FAILED':
        log_group_name = build_details['logs']['groupName']
        log_stream_name = build_details['logs']['streamName']
        logs = get_logs(log_group_name, log_stream_name)
        save_logs_to_file(logs)
        send_email(logs)
        print("Logs saved and email sent.")

if __name__ == '__main__':
    main()
