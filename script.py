import boto3
import traceback
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText
import smtplib


# Configuration
project_name = 'node_build_app'
region_name = 'us-east-1'
ses_sender_email = '' 
recipient_email = ''  # Replace with the recipient's email
smtp_username = ''
smtp_password = ''  # Your Gmail app password

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

def get_logs(log_group_name, log_stream_name, keyword="Reason: exit status 1", lines_before=100):
    """Fetch logs from CloudWatch Logs for a specific log group and stream and extract surrounding logs for the given keyword."""
    client = boto3.client('logs', region_name=region_name)
    try:
        response = client.get_log_events(logGroupName=log_group_name, logStreamName=log_stream_name, limit=10000)  # Fetch a larger batch of logs
        log_messages = [event['message'] for event in response['events']]
        
        # Find the keyword in the logs
        keyword_index = -1
        for i, log in enumerate(log_messages):
            if keyword in log:
                keyword_index = i
                break
        
        if keyword_index == -1:
            print(f"Keyword '{keyword}' not found in logs.")
            return []

        # Extract 100 lines before the keyword, handling out-of-bound cases
        start_index = max(0, keyword_index - lines_before)
        return log_messages[start_index:keyword_index + 1]  # Include the line with the keyword

    except ClientError as e:
        print(f"Error fetching logs: {e}")
        traceback.print_exc()
        return []

def save_logs_to_rtf(logs, filename='build_logs.rtf'):
    """Save logs to an RTF file with highlighted text for specific lines."""
    rtf_content = "{\\rtf1\\ansi\\ansicpg1252\\deff0\\nouicompat\\deflang1033{\\fonttbl{\\f0\\fnil\\fcharset0 Calibri;}}\n"
    rtf_content += "{\\*\\generator Riched20 10.0.18362;}\\viewkind4\\uc1 \n"
    rtf_content += "\\pard\\fs22\\lang9 "  # Set font size and language

    for log in logs:
        # Check if log starts with 'Phase context status code:' and ends with 'Reason: exit status 1'
        if log.startswith("Phase context status code:") and "Reason: exit status 1" in log:
            rtf_content += "{\\colortbl ;\\red255\\green0\\blue0;\\red255\\green255\\blue0;}"
            rtf_content += "\\highlight1\\cf1 " + log.replace("\n", "\\par ") + "\\par "
        else:
            rtf_content += log.replace("\n", "\\par ") + "\\par "

    rtf_content += "}"

    try:
        with open(filename, 'w') as f:
            f.write(rtf_content)
    except Exception as e:
        print(f"Error saving logs to RTF file: {e}")
        traceback.print_exc()

def send_email(logs, filename='build_logs.rtf'):
    """Send an email with the build logs as an attachment."""
    try:
        # Create a multipart message
        msg = MIMEMultipart()
        msg['Subject'] = f'Build Failure Logs for {project_name}'
        msg['From'] = ses_sender_email
        msg['To'] = recipient_email

        # Add body text to the email as MIMEText
        body = "The Log File is Attached Below"
        msg.attach(MIMEText(body, 'plain'))

        # Attach the log file
        with open(filename, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={filename}')
            msg.attach(part)

        # Send email via SMTP server (update this section as needed for your SMTP server)
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(ses_sender_email, [recipient_email], msg.as_string())

        print(f"Email with attachment sent successfully to {recipient_email}")
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
                    # Save logs to an RTF file
                    save_logs_to_rtf(build_logs)

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
