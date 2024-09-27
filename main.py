from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse
import shutil
import os
import requests
import json
from fastapi.middleware.cors import CORSMiddleware
import logging

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configure CORS if necessary
origins = [
    "http://localhost:8000",  # Adjust as needed
    "https://your-frontend-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_presigned_url(file_name, folder_name):
    function_url = 'https://nyludtz4f7mjhemwui4zst2etq0zjcqi.lambda-url.ap-south-1.on.aws/'
    try:
        response = requests.get(function_url, params={'folder': folder_name, 'filename': file_name})
        response.raise_for_status()
        data = response.json()
        logging.info(f"Received presigned URL data: {data}")
        return data.get('uploadURL')
    except requests.exceptions.RequestException as e:
        logging.error(f"Error getting pre-signed URL: {e}")
        return None

def upload_to_s3(presigned_url, file_path):
    try:
        with open(file_path, 'rb') as file:
            file_content = file.read()

        if file_path.lower().endswith('.webm'):
            content_type = 'video/webm'
        elif file_path.lower().endswith(('.jpg', '.jpeg')):
            content_type = 'image/jpeg'
        elif file_path.lower().endswith('.png'):
            content_type = 'image/png'
        else:
            content_type = 'application/octet-stream'

        headers = {'Content-Type': content_type}
        response = requests.put(presigned_url, data=file_content, headers=headers)
        response.raise_for_status()

        logging.info("File uploaded successfully to S3")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error uploading file to S3: {e}")
        return False

def update_interviewee(interviewee_id):
    update_url = 'https://authenticheck-backend.onrender.com/interviewee/update_interviewee'
    headers = {'Content-Type': 'application/json'}
    payload = {'interviewee_id': interviewee_id}

    try:
        response = requests.post(update_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        logging.info("Interviewee updated successfully.")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error updating interviewee: {e}")
        return False

@app.get("/record/", response_class=HTMLResponse)
@app.get("/record", response_class=HTMLResponse)
async def get_record_page(request: Request):
    name = request.query_params.get('name', 'Guest')
    logging.info(f"Serving record page for name: {name}")
    try:
        with open("index.html", "r", encoding="utf-8") as file:
            html_content = file.read().replace('Welcome', f'Welcome {name}')
    except Exception as e:
        logging.error(f"Error loading page: {e}")
        return HTMLResponse(content=f"<h1>Error loading page: {e}</h1>", status_code=500)
    return HTMLResponse(content=html_content, status_code=200)

@app.post("/upload")
async def upload_video(file: UploadFile = File(...), name: str = Form(...)):
    # Sanitize the name to prevent directory traversal or other security issues
    sanitized_name = "".join(c for c in name if c.isalnum() or c in ('-', '_')).rstrip()
    if not sanitized_name:
        return {"error": "Invalid name provided."}

    logging.info(f"Received upload request for name: {sanitized_name}")

    upload_dir = "uploaded_videos"
    os.makedirs(upload_dir, exist_ok=True)

    # Use sanitized_name for the filename
    sanitized_filename = f"{sanitized_name}.webm"
    file_path = os.path.join(upload_dir, sanitized_filename)

    try:
        # Validate file extension
        allowed_extensions = {'.webm', '.jpg', '.jpeg', '.png'}
        _, ext = os.path.splitext(sanitized_filename)
        if ext.lower() not in allowed_extensions:
            logging.warning(f"Unsupported file type: {ext}")
            return {"error": "Unsupported file type."}

        # Save the uploaded file locally
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logging.info(f"Saved file locally at {file_path}")

        # Generate pre-signed URL
        presigned_url = generate_presigned_url(sanitized_filename, sanitized_name)

        if presigned_url:
            logging.info(f"Presigned URL: {presigned_url}")
            # Upload the file to S3
            upload_success = upload_to_s3(presigned_url, file_path)

            if upload_success:
                # Extract interviewee_id without extension
                interviewee_id, _ = os.path.splitext(sanitized_filename)
                update_success = update_interviewee(interviewee_id)

                if not update_success:
                    logging.error("Failed to update interviewee.")
                    return {
                        "filename": sanitized_filename,
                        "status": "upload succeeded, but failed to update interviewee"
                    }
                else:
                    logging.info("Upload and interviewee update successful.")
                    return {"filename": sanitized_filename, "status": "success"}
            else:
                return {"error": "Failed to upload file to S3."}
        else:
            return {"error": "Failed to obtain pre-signed URL. Upload aborted."}
    except Exception as e:
        logging.error(f"Failed to upload file: {e}")
        return {"error": f"Failed to upload file: {e}"}
    finally:
        file.file.close()
        logging.info("Closed file.")

        # Clean up the local file if it exists
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logging.info(f"Removed temporary file: {file_path}")
            except Exception as cleanup_error:
                logging.error(f"Error removing temporary file: {cleanup_error}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
