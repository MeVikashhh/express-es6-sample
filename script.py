import boto3
import smtplib
from email.mime.text import MIMEText
from botocore.exceptions import ClientError
import traceback

# Configuration
project_name = 'node_build_app'
region_name = 'us-east-1'
ses_sender_email = 'vikash.indoqubix@gmail.com' 
recipient_email = 'vikash.indoqubix@gmail.com'  # Replace with the recipient's email
smtp_username = 'vikash.indoqubix@gmail.com'  # Your Gmail address
smtp_password = 'rxhs asuc ygnt rdqv'  # Your Gmail app password

def get_latest_build_id(project_name):
    """Retrieve the latest build ID for a CodeBuild project."""
    client = boto3.client('codebuild', region_name=region_name)
    try:
        response = client.list_builds_for_project(projectName=project_name, sortOrder='DESCENDING')
        return response['ids'][0] if response['ids'] else None
    except ClientError as e:
        print(f"Error fetching build ID: {e}")
        traceback.print_exc()
        return None

def get_build_details(build_id):
    """Retrieve build details for a given build ID."""
    client = boto3.client('codebuild', region_name=region_name)
    try:
        response = client.batch_get_builds(ids=[build_id])
        return response['builds'][0] if response['builds'] else None
    except ClientError as e:
        print(f"Error fetching build details: {e}")
        traceback.print_exc()
        return None

def get_logs(log_group_name, log_stream_name):
    """Fetch logs from CloudWatch Logs for a specific log group and stream."""
    client = boto3.client('logs', region_name=region_name)
    try:
        response = client.get_log_events(logGroupName=log_group_name, logStreamName=log_stream_name, limit=100)
        return [event['message'] for event in response['events']]
    except ClientError as e:
        print(f"Error fetching logs: {e}")
        traceback.print_exc()
        return []

def save_logs_to_file(logs, filename='build_logs.txt'):
    """Save logs to a file."""
    try:
        with open(filename, 'w') as f:
            for log in logs:
                f.write(f"{log}\n")
    except Exception as e:
        print(f"Error saving logs to file: {e}")
        traceback.print_exc()

def send_email(logs):
    """Send an email using Gmail SMTP server with the build logs."""
    try:
        msg = MIMEText("\n".join(logs))
        msg['Subject'] = f'Build Failure Logs for {project_name}'
        msg['From'] = ses_sender_email
        msg['To'] = recipient_email

        # Send email via Gmail SMTP server
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(ses_sender_email, [recipient_email], msg.as_string())
        
        print(f"Email sent successfully to {recipient_email}")
    except Exception as e:
        print(f"Error sending email: {e}")
        traceback.print_exc()

def main():
    try:
        # Retrieve the latest build ID
        latest_build_id = get_latest_build_id(project_name)
        if latest_build_id:
            # Retrieve build details
            build_details = get_build_details(latest_build_id)
            if build_details:
                log_group_name = build_details['logs']['groupName']
                log_stream_name = build_details['logs']['streamName']
                
                # Fetch logs from CloudWatch
                build_logs = get_logs(log_group_name, log_stream_name)

                if build_logs:
                    # Save logs to a file
                    save_logs_to_file(build_logs)

                    # Send the logs via email
                    send_email(build_logs)
                else:
                    print("No logs found.")
            else:
                print("Build details not found.")
        else:
            print("No build ID found.")
    except Exception as e:
        print(f"Error occurred: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
