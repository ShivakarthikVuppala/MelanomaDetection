import os
import re
from huggingface_hub import HfApi, create_repo

def main():
    # 1. Read token from .env
    token = None
    with open("c:\\SDC-II\\.env", "r") as f:
        for line in f:
            if "HF_TOKEN" in line:
                match = re.search(r'HF_TOKEN\s*=\s*([a-zA-Z0-9_]+)', line)
                if match:
                    token = match.group(1)
                    break
    
    if not token:
        print("Error: Could not find HF_TOKEN in .env")
        return

    print("Successfully found HF_TOKEN.")
    
    api = HfApi(token=token)
    
    # 2. Get user info
    try:
        user_info = api.whoami()
        username = user_info["name"]
        print(f"Logged in as {username}")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    # 3. Create Model repo instead of Space to avoid PRO requirement
    repo_id = f"{username}/melanoma-classifier"
    print(f"Creating or verifying MODEL repository: {repo_id}")
    try:
        create_repo(repo_id=repo_id, repo_type="model", token=token, exist_ok=True)
        print("Repository ready.")
    except Exception as e:
        print(f"Failed to create repository: {e}")
        return

    # 4. Upload huggingface_space directory files
    folder_path = "c:\\SDC-II\\huggingface_space"
    print(f"Uploading Space files (Gradio app) to model repo: {folder_path}")
    try:
        api.upload_folder(
            folder_path=folder_path,
            repo_id=repo_id,
            repo_type="model"
        )
        print("Folder uploaded successfully.")
    except Exception as e:
        print(f"Failed to upload folder: {e}")

    # 5. Upload model checkpoint
    model_path = "c:\\SDC-II\\checkpoints\\best_swin_checkpoint.pth"
    print(f"Uploading model checkpoint: {model_path}")
    try:
        api.upload_file(
            path_or_fileobj=model_path,
            path_in_repo="best_swin_checkpoint.pth",
            repo_id=repo_id,
            repo_type="model"
        )
        print("Model checkpoint uploaded successfully.")
    except Exception as e:
        print(f"Failed to upload model: {e}")
        
    print(f"\nDone! Your repository is accessible at: https://huggingface.co/{repo_id}")

if __name__ == "__main__":
    main()
