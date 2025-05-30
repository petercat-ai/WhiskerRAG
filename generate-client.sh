#!/bin/bash

# default values
PACKAGE_NAME="@petercatai/whisker-client"
OUTPUT_DIR="./.client"
VERSION_PREFIX="0.1"
NPM_TOKEN="${NPM_AUTH_TOKEN}"

# Validate NPM token
if [ -z "$NPM_TOKEN" ]; then
    echo "::error::NPM token is missing"
    exit 1
fi

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --publish) PUBLISH=true ;;
        --ENVIRONMENT=*) ENVIRONMENT="${1#*=}" ;;
        --API_URL=*) API_URL="${1#*=}" ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Validate required parameters
if [ -z "$API_URL" ]; then
    echo "Error: --API_URL is required"
    exit 1
fi

if [ -z "$ENVIRONMENT" ]; then
    echo "Error: --ENVIRONMENT is required"
    exit 1
fi

# Remove trailing slash from API URL if present
API_URL=${API_URL%/}

# Set npm tag based on environment
NPM_TAG=$([ "$ENVIRONMENT" = "Production" ] && echo "latest" || echo "dev")

# Set version based on environment
TIMESTAMP=$(date +%Y%m%d%H%M)
VERSION="${VERSION_PREFIX}.${TIMESTAMP}$([ "$ENVIRONMENT" != "Production" ] && echo "-dev" || echo "")"

echo "Configuration:"
echo "  Environment: ${ENVIRONMENT}"
echo "  API URL: ${API_URL}"
echo "  Version: ${VERSION}"
echo "  NPM tag: ${NPM_TAG}"

# Make sure the output directory exists
mkdir -p "$OUTPUT_DIR"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "npm is not installed"
    exit 1
fi

# Install swagger-typescript-api globally
echo "Installing swagger-typescript-api..."
npm install -g swagger-typescript-api

echo "Generating client with version: $VERSION"

# Get the OpenAPI spec
echo "Fetching OpenAPI spec from ${API_URL}/openapi.json"
curl -f "${API_URL}/openapi.json" -o openapi.json || {
    echo "Failed to fetch OpenAPI spec"
    exit 1
}

# generate the client code
echo "Generating client code..."
swagger-typescript-api generate \
    -p ./openapi.json \
    -o $OUTPUT_DIR \
    --name api.ts \
    --type-prefix I \
    --module-name-index 1

# create package.json
echo "Creating package.json..."
cat > $OUTPUT_DIR/package.json << EOF
{
    "name": "${PACKAGE_NAME}",
    "version": "${VERSION}",
    "description": "Generated API client (${ENVIRONMENT})",
    "main": "dist/api.js",
    "types": "dist/api.d.ts",
    "files": [
        "dist"
    ],
    "scripts": {
        "build": "tsc",
        "prepare": "npm run build"
    },
    "publishConfig": {
        "access": "public",
        "tag": "${NPM_TAG}"
    }
}
EOF

# create tsconfig.json
echo "Creating tsconfig.json..."
cat > $OUTPUT_DIR/tsconfig.json << EOF
{
    "compilerOptions": {
        "target": "es2017",
        "module": "commonjs",
        "declaration": true,
        "outDir": "./dist",
        "strict": true,
        "esModuleInterop": true,
        "skipLibCheck": true,
        "forceConsistentCasingInFileNames": true
    },
    "include": ["*.ts"],
    "exclude": ["node_modules", "dist"]
}
EOF

# create .npmignore
echo "Creating .npmignore..."
cat > $OUTPUT_DIR/.npmignore << EOF
src/
tsconfig.json
.github
EOF

# install dependencies
echo "Installing dependencies..."
cd $OUTPUT_DIR
npm install typescript @types/node axios --save-dev

# build the client
echo "Building..."
npm run build

# publish the package if --publish is set
publish_package() {
    local token=$1
    
    if [ -z "$token" ]; then
        echo "Error: NPM token is required"
        return 1
    fi
    
    cat > .npmrc << EOF
//registry.npmjs.org/:_authToken=${token}
registry=https://registry.npmjs.org/
always-auth=true
EOF
    
    npm publish --access public --tag $NPM_TAG || {
        rm -f .npmrc
        echo "Failed to publish package"
        return 1
    }
    
    rm -f .npmrc
    
    echo "Successfully published package ${PACKAGE_NAME}@${VERSION}"
    return 0
}

if [ "$PUBLISH" = true ]; then
    if ! publish_package "$NPM_TOKEN"; then
        echo "Failed to publish package"
        exit 1
    fi
fi

echo "Client generation completed successfully!"
echo "Output directory: $OUTPUT_DIR"
echo "Version: $VERSION"
echo "NPM tag: $NPM_TAG"
