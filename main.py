from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse
import shutil
import os
from utils import generate_presigned_url, upload_to_s3
app = FastAPI()


@app.get("/record", response_class=HTMLResponse)
async def get_record_page(request: Request):
    name = request.query_params.get('name', 'Guest')
    with open("index.html", "r") as file:
        html_content = file.read().replace('Welcome', f'Welcome {name}')
        return HTMLResponse(content=html_content, status_code=200)

@app.post("/upload")
async def upload_video(file: UploadFile = File(...), name: str = Form(...)):
    upload_dir = "uploaded_videos"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    print(name)
    # Upload the file to S3
    presigned_url = generate_presigned_url(file.filename, name)
    if presigned_url:
        upload_to_s3(presigned_url, file_path)
    else:
        return {"error": "Failed to obtain pre-signed URL. Upload aborted."} 
    os.remove(file_path)  # Clean up the local file
    return {"filename": file.filename, "status": "success"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
