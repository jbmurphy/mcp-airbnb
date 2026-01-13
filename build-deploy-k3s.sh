#!/bin/bash
# Build, push and deploy mcp-airbnb to K3s

set -e

IMAGE_NAME="registry.local.jbmurphy.com/mcp-airbnb:latest"
APP_NAME="mcp-airbnb"

# Create or use buildx builder for multi-platform
if ! docker buildx ls | grep -q multiplatform; then
    echo "Creating multi-platform builder..."
    docker buildx create --name multiplatform --use
else
    echo "Using existing multi-platform builder..."
    docker buildx use multiplatform
fi

echo "Building multi-architecture $APP_NAME Docker image (amd64 and arm64)..."
docker buildx build --platform linux/amd64,linux/arm64 -t "$IMAGE_NAME" --push .

echo "Image pushed: $IMAGE_NAME"
echo ""

# Deploy to K3s
echo "Deploying to K3s..."
kubectl apply -f k3s-deployment.yaml

echo "Restarting deployment to pull new image..."
kubectl rollout restart deployment/$APP_NAME

echo "Waiting for rollout to complete..."
kubectl rollout status deployment/$APP_NAME --timeout=120s

echo ""
echo "Deployment complete!"
echo ""
echo "Check status:"
echo "   kubectl get pods -l app=$APP_NAME"
echo "   kubectl logs -f deployment/$APP_NAME"
