import requests
import json

# S3 bucket details

def generate_presigned_url(file_name, folder_name):
    # Function URL (Replace with your Lambda function's URL)
    function_url = 'https://nyludtz4f7mjhemwui4zst2etq0zjcqi.lambda-url.ap-south-1.on.aws/'
    try:
        # Make GET request to Lambda function URL to get pre-signed URL
        response = requests.get(function_url, params={'folder': folder_name, 'filename': file_name})
        response.raise_for_status()  # Raise error for bad response status

        # Extract pre-signed URL from response
        data = response.json()
        print(f"Received presigned URL data: {data}")
        return data.get('uploadURL')
    except requests.exceptions.RequestException as e:
        print(f"Error getting pre-signed URL: {e}")
        return None

def upload_to_s3(presigned_url, file_path):
    try:
        # Read file content
        with open(file_path, 'rb') as file:
            file_content = file.read()

        # Determine the correct Content-Type based on file extension
        if file_path.lower().endswith('.webm'):
            content_type = 'video/webm'
        elif file_path.lower().endswith('.jpg') or file_path.lower().endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif file_path.lower().endswith('.png'):
            content_type = 'image/png'
        else:
            content_type = 'application/octet-stream'  # Default binary type

        # Upload file to S3 using pre-signed URL
        headers = {'Content-Type': content_type}
        response = requests.put(presigned_url, data=file_content, headers=headers)
        response.raise_for_status()  # Raise error for bad response status

        print("File uploaded successfully to S3")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error uploading file to S3: {e}")
        return False

def update_interviewee(interviewee_id, file_name, s3_url):
    update_url = 'https://authenticheck-backend.onrender.com/interviewee/update_interviewee'
    headers = {'Content-Type': 'application/json'}
    payload = {
        'interviewee_id': interviewee_id,
    }

    try:
        response = requests.post(update_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Raise error for bad response status

        print("Interviewee updated successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error updating interviewee: {e}")
        return False

def main():
    folder_name = 'harsh'  # Assuming 'harsh' is the folder name in S3
    file_name = 'Harsh.webm' 
    file_path = 'Harsh.webm' 
    interviewee_id = '12345'  # Replace with the actual interviewee ID

    # Generate pre-signed URL
    presigned_url = generate_presigned_url(file_name, folder_name)

    if presigned_url:
        print(f"Presigned URL: {presigned_url}")
        # Upload file to S3 using pre-signed URL
        upload_success = upload_to_s3(presigned_url, file_path)

        if upload_success:
            # Optionally, construct the S3 URL if needed
            s3_url = f"https://{YOUR_S3_BUCKET_NAME}.s3.amazonaws.com/{folder_name}/{file_name}"
            # Update interviewee information
            update_success = update_interviewee(interviewee_id)

            if not update_success:
                print("Failed to update interviewee information.")
        else:
            print("File upload failed. Skipping interviewee update.")
    else:
        print("Failed to obtain pre-signed URL. Upload aborted.")

if __name__ == "__main__":
    main()
