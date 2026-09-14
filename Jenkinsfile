pipeline {
  agent any
  environment { IMAGE = "ghcr.io/example/hybrid-rag:${BUILD_NUMBER}"; ACR_IMAGE = "${AZURE_ACR_LOGIN_SERVER}/hybrid-rag:${BUILD_NUMBER}" }
  stages {
    stage('Test') {steps {sh 'python -m pytest -q'}}
    stage('Build') {steps {sh 'docker build -t $IMAGE .'}}
    stage('Publish GHCR') {steps {withCredentials([string(credentialsId: 'ghcr-token', variable: 'TOKEN')]) {sh 'echo "$TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin && docker push $IMAGE'}}}
    stage('Publish ACR') {when {expression {env.AZURE_ACR_LOGIN_SERVER != null}}; steps {sh 'az acr login --name "$AZURE_ACR_NAME" && docker tag $IMAGE $ACR_IMAGE && docker push $ACR_IMAGE'}}}
  }
}
