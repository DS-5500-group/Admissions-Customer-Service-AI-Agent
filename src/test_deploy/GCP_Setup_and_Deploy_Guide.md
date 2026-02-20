# GCP Cloud Run: Setup & Deployment Guide

## Prerequisites

- A Google account (Gmail)
- Project owner access (you should have received an email invitation — accept it first)
- [Google Cloud SDK (gcloud CLI)](https://cloud.google.com/sdk/docs/install) installed on your machine

---

## 1. Authenticate and Set Project

Open your terminal and run:

```bash
gcloud auth login
```

This opens a browser window. Sign in with the Google account that was granted access.

Then set the project so you don't have to specify it on every command:

```bash
gcloud config set project ds5500-487815
```



Verify it's set correctly:

```bash
gcloud config list
```

---

## 2. Enable Required APIs (One-Time)

These may already be enabled. Running the commands again is harmless:

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable run.googleapis.com
```

---

## 3. Configure Docker Authentication for Artifact Registry

This lets you push images to the project's Docker repository. Only needed once:

```bash
gcloud auth configure-docker  us-central1-docker.pkg.dev
```

---

## 4. Project Structure

Your project directory should look like:

```
my-app/
├── echo.py              # Your FastAPI 
├── requirements.txt     # Python dependencies
└── Dockerfile
```

**requirements.txt:**

```
fastapi
uvicorn
twilio
python-multipart
```

**Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

> **Note:** `main:app` means uvicorn looks for a variable called `app` inside a file called `main.py`. If your file is named `echo.py`, change it to `echo:app`.

---

## 5. Build and Push the Image

From your project directory (where the Dockerfile is), run:

```bash
gcloud builds submit --tag  us-central1-docker.pkg.dev/ds5500-487815/test-repo/echo-test
```



This uploads your source code to Google Cloud Build, builds the Docker image remotely, and pushes it to Artifact Registry. You do **not** need Docker installed locally for this.

---

## 6. Deploy to Cloud Run

**First deployment:**

```bash
gcloud run deploy echo-test --image  us-central1-docker.pkg.dev/ds5500-487815/test-repo/echo-test --region  us-central1 --allow-unauthenticated
```

`<SERVICE_NAME>` is what appears in the Cloud Run console (e.g., `echo-test`). `--allow-unauthenticated` is required so that Twilio can reach your endpoints without a GCP auth token.

**Windows PowerShell multi-line version** (use backticks for line continuation):

```powershell
gcloud run deploy echo-test `
  --image  us-central1-docker.pkg.dev/ds5500-487815/test-repo/echo-test `
  --region  us-central1 `
  --allow-unauthenticated `
  --memory 256Mi `
  --cpu 1 `
  --min-instances 0 `
  --max-instances 3 `
  --timeout 300
```

After deployment, Cloud Run outputs a URL like `https://echo-test-xxxxx-ue.a.run.app`. This is your service URL.

---

## 7. Deploying Updates (Revisions)

When you change your code and want to redeploy:

```bash
# Step 1: Rebuild and push (overwrites the previous image)
gcloud builds submit --tag  us-central1-docker.pkg.dev/ds5500-487815/test-repo/echo-test

# Step 2: Redeploy (tells Cloud Run to use the new image)
gcloud run deploy echo-test --image  us-central1-docker.pkg.dev/ds5500-487815/test-repo/echo-test --region  us-central1
```

Both steps are required. `builds submit` pushes the new image; `run deploy` tells Cloud Run to pull and use it.

---

## 8. Viewing Logs

In the Cloud Run console, click your service and go to the **Logs** tab. Or from the terminal:

```bash
gcloud run services logs read echo-test --region  us-central1
```

Any `print()` statements in your Python code will appear here.

---

## 9. Twilio Webhook Configuration

After deploying, configure Twilio to point at your Cloud Run service:

1. Go to the [Twilio Console](https://console.twilio.com/) → **Phone Numbers** → **Manage** → **Active Numbers**.
2. Click your phone number.
3. Under **Voice & Fax**, set **"A Call Comes In"** to **Webhook**.
4. Paste your Cloud Run URL with the route (e.g., `https://echo-test-xxxxx-ue.a.run.app/`).
5. Set method to **HTTP POST**.
6. Save.

---

## Quick Reference

| Action | Command |
|--------|---------|
| Authenticate | `gcloud auth login` |
| Set project | `gcloud config set project ds5500-487815` |
| Build & push image | `gcloud builds submit --tag  us-central1-docker.pkg.dev/ds5500-487815/test-repo/echo-test` |
| Deploy | `gcloud run deploy echo-test --image  us-central1-docker.pkg.dev/ds5500-487815/test-repo/echo-test --region  us-central1 --allow-unauthenticated` |
| View logs | `gcloud run services logs read echo-test --region  us-central1` |
