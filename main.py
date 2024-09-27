from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse
import shutil
import os
import requests
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from starlette.responses import RedirectResponse


app = FastAPI()

def generate_presigned_url(file_name, folder_name):
    function_url = 'https://nyludtz4f7mjhemwui4zst2etq0zjcqi.lambda-url.ap-south-1.on.aws/'
    try:
        response = requests.get(function_url, params={'folder': folder_name, 'filename': file_name})
        response.raise_for_status()
        data = response.json()
        print(f"Received presigned URL data: {data}")
        return data.get('uploadURL')
    except requests.exceptions.RequestException as e:
        print(f"Error getting pre-signed URL: {e}")
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

        print("File uploaded successfully to S3")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error uploading file to S3: {e}")
        return False

def update_interviewee(interviewee_id):
    update_url = 'https://authenticheck-backend.onrender.com/interviewee/update_interviewee'
    headers = {'Content-Type': 'application/json'}
    payload = {'interviewee_id': interviewee_id}

    try:
        response = requests.post(update_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        print("Interviewee updated successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error updating interviewee: {e}")
        return False

@app.get("/record/", response_class=HTMLResponse)
@app.get("/record", response_class=HTMLResponse)
async def get_record_page(request: Request):
    name = request.query_params.get('name', 'Guest')
    try:
        with open("index.html", "r", encoding="utf-8") as file:
            html_content = file.read().replace('Welcome', f'Welcome {name}')
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error loading page: {e}</h1>", status_code=500)
    return HTMLResponse(content=html_content, status_code=200)


@app.post("/upload")
async def upload_video(file: UploadFile = File(...), name: str = Form(...)):
    upload_dir = "uploaded_videos"
    os.makedirs(upload_dir, exist_ok=True)

    # Use 'name' for the filename instead of the uploaded file's original name
    sanitized_filename = f"{name}.webm"  # Using name from form as the filename
    file_path = os.path.join(upload_dir, sanitized_filename)

    try:
        # Validate file extension
        allowed_extensions = {'.webm', '.jpg', '.jpeg', '.png'}
        _, ext = os.path.splitext(sanitized_filename)
        if ext.lower() not in allowed_extensions:
            return {"error": "Unsupported file type."}

        # Save the uploaded file locally
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Generate pre-signed URL
        presigned_url = generate_presigned_url(sanitized_filename, name)

        if presigned_url:
            print(f"Presigned URL: {presigned_url}")
            # Upload the file to S3
            upload_success = upload_to_s3(presigned_url, file_path)

            if upload_success:
                # Extract interviewee_id without extension
                interviewee_id, _ = os.path.splitext(sanitized_filename)
                update_success = update_interviewee(interviewee_id)

                if not update_success:
                    return {
                        "filename": sanitized_filename,
                        "status": "upload succeeded, but failed to update interviewee"
                    }
                else:
                    return {"filename": sanitized_filename, "status": "success"}
            else:
                return {"error": "Failed to upload file to S3."}
        else:
            return {"error": "Failed to obtain pre-signed URL. Upload aborted."}
    except Exception as e:
        return {"error": f"Failed to upload file: {e}"}
    finally:
        file.file.close()

        # Clean up the local file if it exists
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as cleanup_error:
                print(f"Error removing temporary file: {cleanup_error}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
