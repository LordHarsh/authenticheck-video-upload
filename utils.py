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
        print(data)
        return data['uploadURL']
    except requests.exceptions.RequestException as e:
        print(f"Error getting pre-signed URL: {e}")
        return None

def upload_to_s3(presigned_url, file_path):
    try:
        # Read file content
        with open(file_path, 'rb') as file:
            file_content = file.read()

        # Upload file to S3 using pre-signed URL
        response = requests.put(presigned_url, data=file_content, headers={'Content-Type': 'image/jpeg'})
        response.raise_for_status()  # Raise error for bad response status

        print("File uploaded successfully to S3")
    except requests.exceptions.RequestException as e:
        print(f"Error uploading file to S3: {e}")

def main():
    folder_name = 'harsh'
    file_name = 'Harsh.webm' 
    file_path = 'Harsh.webm' 
    # Generate pre-signed URL
    presigned_url = generate_presigned_url(file_name, folder_name)

    if presigned_url:
        # Upload file to S3 using pre-signed URL
        print(presigned_url)
        upload_to_s3(presigned_url, file_path)

    else:
        print("Failed to obtain pre-signed URL. Upload aborted.")

if __name__ == "__main__":
    main()