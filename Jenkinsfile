pipeline {
  agent any
  options { timestamps(); disableConcurrentBuilds() }
  parameters {
    string(name: 'IMAGE_REPOSITORY', defaultValue: 'ghcr.io/amazen33/omni-stream-rag-mesh', description: 'Published container repository (no mutable latest tag)')
    string(name: 'IMAGE_TAG', defaultValue: 'candidate', description: 'Immutable image tag or digest selected for this build')
    booleanParam(name: 'PUBLISH_GHCR', defaultValue: false, description: 'Push to GHCR using ghcr-token')
    booleanParam(name: 'PUBLISH_ACR', defaultValue: false, description: 'Push to ACR using azure-sp credentials')
  }
  environment { IMAGE = "${IMAGE_REPOSITORY}:${IMAGE_TAG}"; ACR_IMAGE = "${AZURE_ACR_LOGIN_SERVER}/hybrid-rag:${IMAGE_TAG}" }
  stages {
    stage('Set up Python environment') {
      steps { sh 'python3 -m venv .venv && . .venv/bin/activate && python -m pip install --upgrade pip && python -m pip install -r requirements.txt -r ansible/requirements-controller.txt && python -m pip check' }
    }
    stage('Test') { steps { sh '. .venv/bin/activate && python -m pytest -q' } }
    stage('Downstream Chaos & Resilience Gates') {
      steps { sh '. .venv/bin/activate && python -m pytest -v tests/chaos' }
    }
    stage('Build') { steps { sh 'docker build --pull -t "$IMAGE" .' } }
    stage('Trivy image gate') {
      steps { sh 'trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed "$IMAGE"' }
    }
    stage('Trivy IaC gate') {
      steps { sh 'trivy config --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed .' }
    }
    stage('Publish GHCR') {
      when { expression { params.PUBLISH_GHCR } }
      steps {
        withCredentials([usernamePassword(credentialsId: 'ghcr-token', usernameVariable: 'GHCR_USER', passwordVariable: 'TOKEN')]) {
          sh 'echo "$TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin && docker push "$IMAGE"'
        }
      }
    }
    stage('Publish ACR') {
      when { expression { params.PUBLISH_ACR && env.AZURE_ACR_LOGIN_SERVER?.trim() } }
      steps {
        withCredentials([usernamePassword(credentialsId: 'azure-sp', usernameVariable: 'AZURE_CLIENT_ID', passwordVariable: 'AZURE_CLIENT_SECRET')]) {
          sh 'az login --service-principal -u "$AZURE_CLIENT_ID" -p "$AZURE_CLIENT_SECRET" --tenant "$AZURE_TENANT_ID" && az acr login --name "$AZURE_ACR_NAME" && docker tag "$IMAGE" "$ACR_IMAGE" && docker push "$ACR_IMAGE"'
        }
      }
    }
  }
}
