# Project Image Packaging
In the sample project `sample_standard_app`, we provide a script that automates the process of packaging an aU project into an image. This script helps you create an image based on the CentOS 8 system, including the Python runtime environment and project dependencies. You can then refer to [Docker Container Deployment](./Docker_Container_Deployment.md) and [K8S Deployment](./K8S_Deployment.md) to deploy your aU application.

## Execution Steps
```shell
# 1. Navigate to the image_build directory. Replace sample_standard_app with your actual project name.
cd xxx/xxx/sample_standard_app/image_build

chmod +x start_build.sh
./start_build.sh
```

## Configurable Parameters
You can modify the following configurations in the script:
```shell
IMAGE_NAME=${PROJECT_NAME}
IMAGE_TAG="latest"
```
- `IMAGE_NAME` specifies the output image name, with the default value set to your project directory name.
- `IMAGE_TAG` specifies the output image tag, with the default value set to latest.