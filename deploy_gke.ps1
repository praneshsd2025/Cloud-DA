# GazeboExpress GKE Deployment Script
$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " GazeboExpress - Autonomous GKE Deployment" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Verify GKE credentials
Write-Host "`n[1/5] Checking Google Cloud and GKE connection..." -ForegroundColor Yellow
try {
    kubectl get namespace gazeboexpress | Out-Null
    Write-Host "  -> Connected to GKE cluster successfully." -ForegroundColor Green
} catch {
    Write-Host "  -> Refreshing GKE credentials..." -ForegroundColor Yellow
    gcloud container clusters get-credentials gazeboexpress-cluster --region asia-south1 --project gazeboexpress
}

# 2. Build Docker images
Write-Host "`n[2/5] Building Docker images..." -ForegroundColor Yellow
Write-Host "  -> Building backend image (praneshsd/gazeboexpress-backend:v6)..."
docker build -t praneshsd/gazeboexpress-backend:v6 .\backend

Write-Host "  -> Building frontend image (praneshsd/gazeboexpress-frontend:v12)..."
docker build -t praneshsd/gazeboexpress-frontend:v12 .\frontend

# 3. Push Docker images
Write-Host "`n[3/5] Pushing Docker images to registry..." -ForegroundColor Yellow
docker push praneshsd/gazeboexpress-backend:v6
docker push praneshsd/gazeboexpress-frontend:v12

# 4. Apply Kubernetes manifests
Write-Host "`n[4/5] Applying Kubernetes manifests (Deployments, Services, Gateway, TLS Secret)..." -ForegroundColor Yellow
kubectl apply -f .\kubernetes\

# 5. Wait for rollout
Write-Host "`n[5/5] Waiting for deployment rollouts to complete..." -ForegroundColor Yellow
kubectl rollout status deployment/backend -n gazeboexpress --timeout=180s
kubectl rollout status deployment/frontend -n gazeboexpress --timeout=180s

Write-Host "`n==================================================" -ForegroundColor Green
Write-Host " GazeboExpress GKE Deployment Completed Successfully!" -ForegroundColor Green
Write-Host " Live Website: https://35-207-230-72.nip.io" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

