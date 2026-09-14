pipeline {
  agent any
  options { timestamps(); disableConcurrentBuilds() }
  parameters {
    booleanParam(name: 'PUBLISH_GHCR', defaultValue: false, description: 'Push to GHCR using ghcr-token')
    booleanParam(name: 'PUBLISH_ACR', defaultValue: false, description: 'Push to ACR using azure-sp credentials')
  }
  environment { IMAGE = "ghcr.io/example/hybrid-rag:${BUILD_TAG}"; ACR_IMAGE = "${AZURE_ACR_LOGIN_SERVER}/hybrid-rag:${BUILD_TAG}" }
  stages {
    stage('Test') { steps { sh 'python -m pytest -q' } }
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
