#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PACKAGE_NAME="project-core"
VERSION="1.0.0"
ARCH="all"
MAINTAINER="Matteo Galvagni <galvagni.matteo@protonmail.com>"
DESCRIPTION="Docker-based microservices alarm system"
INSTALL_DIR="/opt/project-core"
SERVICE_NAME="alarm.service"
BUILD_DIR="./build"
DEB_DIR="${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}"

echo -e "${GREEN}=== Building DEB Package for Project Core ===${NC}"

echo -e "${YELLOW}Checking prerequisites...${NC}"

if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create a .env file based on .env.example before building the package."
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo -e "${RED}Error: git is not installed!${NC}"
    exit 1
fi

if ! command -v dpkg-deb &> /dev/null; then
    echo -e "${RED}Error: dpkg-deb is not installed!${NC}"
    echo "Please install dpkg-dev package: sudo apt-get install dpkg-dev"
    exit 1
fi

echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf "${BUILD_DIR}"

echo -e "${YELLOW}Creating package structure...${NC}"
mkdir -p "${DEB_DIR}/DEBIAN"
mkdir -p "${DEB_DIR}${INSTALL_DIR}"
mkdir -p "${DEB_DIR}/etc/systemd/system"
mkdir -p "${DEB_DIR}/usr/local/bin"
mkdir -p "${BUILD_DIR}"

echo -e "${YELLOW}Cloning repository with submodules...${NC}"
TEMP_CLONE_DIR="${BUILD_DIR}/temp_clone"
mkdir -p "${TEMP_CLONE_DIR}"

cp -r . "${TEMP_CLONE_DIR}/" 2>/dev/null || true
cd "${TEMP_CLONE_DIR}"

echo -e "${YELLOW}Initializing and updating git submodules...${NC}"
git submodule init
git submodule update --recursive

for submodule in microservices/project-proxy \
                 microservices/notifications-manager \
                 microservices/local-audio-manager \
                 microservices/project-auth \
                 microservices/devices-manager \
                 microservices/project-frontend; do
    if [ ! -d "$submodule" ] || [ -z "$(ls -A $submodule)" ]; then
        echo -e "${RED}Error: Submodule $submodule not properly initialized${NC}"
        exit 1
    fi
done

cd - > /dev/null

echo -e "${YELLOW}Copying project files...${NC}"
cp -r "${TEMP_CLONE_DIR}/." "${DEB_DIR}${INSTALL_DIR}/"

find "${DEB_DIR}${INSTALL_DIR}" -type d -name ".git" -exec rm -rf {} + 2>/dev/null || true
find "${DEB_DIR}${INSTALL_DIR}" -name ".gitignore" -delete 2>/dev/null || true
find "${DEB_DIR}${INSTALL_DIR}" -name ".gitmodules" -delete 2>/dev/null || true

echo -e "${YELLOW}Copying systemd service file...${NC}"
if [ ! -f "alarm.service" ]; then
    echo -e "${RED}Error: alarm.service file not found!${NC}"
    exit 1
fi

cp "alarm.service" "${DEB_DIR}/etc/systemd/system/${SERVICE_NAME}"
sed -i "s|/home/pi/project-core|${INSTALL_DIR}|g" "${DEB_DIR}/etc/systemd/system/${SERVICE_NAME}"

echo -e "${YELLOW}Creating utility scripts...${NC}"

cat > "${DEB_DIR}/usr/local/bin/project-core-ctl" << 'EOF'
#!/bin/bash

INSTALL_DIR="/opt/project-core"
SERVICE_NAME="alarm.service"

case "$1" in
    start)
        echo "Starting Project Core..."
        sudo systemctl start ${SERVICE_NAME}
        ;;
    stop)
        echo "Stopping Project Core..."
        sudo systemctl stop ${SERVICE_NAME}
        ;;
    restart)
        echo "Restarting Project Core..."
        sudo systemctl restart ${SERVICE_NAME}
        ;;
    status)
        sudo systemctl status ${SERVICE_NAME}
        ;;
    logs)
        cd ${INSTALL_DIR}
        sudo docker compose logs -f ${@:2}
        ;;
    ps)
        cd ${INSTALL_DIR}
        sudo docker compose ps
        ;;
    update)
        echo "Pulling latest Docker images..."
        cd ${INSTALL_DIR}
        sudo docker compose pull
        sudo systemctl restart ${SERVICE_NAME}
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|ps|update}"
        echo "  start   - Start the Project Core services"
        echo "  stop    - Stop the Project Core services"
        echo "  restart - Restart the Project Core services"
        echo "  status  - Show service status"
        echo "  logs    - Show Docker Compose logs (optionally specify service name)"
        echo "  ps      - Show running containers"
        echo "  update  - Pull latest Docker images and restart"
        exit 1
        ;;
esac
EOF

chmod +x "${DEB_DIR}/usr/local/bin/project-core-ctl"

echo -e "${YELLOW}Creating DEBIAN control file...${NC}"
cat > "${DEB_DIR}/DEBIAN/control" << EOF
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: misc
Priority: optional
Architecture: ${ARCH}
Depends: docker.io | docker-ce, docker-compose-plugin | docker-compose, git, openssl, curl
Maintainer: ${MAINTAINER}
Description: ${DESCRIPTION}
 This package installs and configures the Project Core microservices
 infrastructure using Docker Compose. It includes multiple services
 for device management, notifications, audio management, authentication,
 and a web frontend.
EOF

echo -e "${YELLOW}Creating post-installation script...${NC}"
cat > "${DEB_DIR}/DEBIAN/postinst" << EOF
#!/bin/bash
set -e

echo "Configuring Project Core..."

chown -R root:root ${INSTALL_DIR}
chmod 755 ${INSTALL_DIR}

systemctl daemon-reload

systemctl enable ${SERVICE_NAME}

echo "Starting Project Core service..."
systemctl start ${SERVICE_NAME} || echo "Warning: Could not start service automatically. Please start it manually."

echo ""
echo "================================================================"
echo " Project Core has been successfully installed!"
echo "================================================================"
echo ""
echo "Installation directory: ${INSTALL_DIR}"
echo ""
echo "To start the service, run:"
echo "  sudo systemctl start ${SERVICE_NAME}"
echo "  or"
echo "  sudo project-core-ctl start"
echo ""
echo "To check the status:"
echo "  sudo systemctl status ${SERVICE_NAME}"
echo "  or"
echo "  sudo project-core-ctl status"
echo ""
echo "To view logs:"
echo "  sudo project-core-ctl logs"
echo ""
echo "Available commands:"
echo "  project-core-ctl {start|stop|restart|status|logs|ps|update}"
echo ""
echo "The service will start automatically on system boot."
echo "================================================================"
echo ""

exit 0
EOF

chmod 755 "${DEB_DIR}/DEBIAN/postinst"

echo -e "${YELLOW}Creating pre-removal script...${NC}"
cat > "${DEB_DIR}/DEBIAN/prerm" << EOF
#!/bin/bash
set -e

echo "Stopping Project Core services..."

if systemctl is-active --quiet ${SERVICE_NAME}; then
    systemctl stop ${SERVICE_NAME}
fi

if systemctl is-enabled --quiet ${SERVICE_NAME}; then
    systemctl disable ${SERVICE_NAME}
fi

if [ -f "${INSTALL_DIR}/docker-compose.yaml" ]; then
    cd ${INSTALL_DIR}
    docker compose down -v 2>/dev/null || true
fi

exit 0
EOF

chmod 755 "${DEB_DIR}/DEBIAN/prerm"

echo -e "${YELLOW}Creating post-removal script...${NC}"
cat > "${DEB_DIR}/DEBIAN/postrm" << EOF
#!/bin/bash
set -e

systemctl daemon-reload

if [ "\$1" = "purge" ]; then
    echo "Purging Project Core data..."

    docker volume ls --format '{{.Name}}' | grep -E '^project-core_' | xargs -r docker volume rm 2>/dev/null || true

    if [ -d "${INSTALL_DIR}" ]; then
        rm -rf "${INSTALL_DIR}"
    fi
fi

echo "Project Core has been removed."

exit 0
EOF

chmod 755 "${DEB_DIR}/DEBIAN/postrm"

INSTALLED_SIZE=$(du -sk "${DEB_DIR}" | cut -f1)
echo "Installed-Size: ${INSTALLED_SIZE}" >> "${DEB_DIR}/DEBIAN/control"

echo -e "${YELLOW}Building DEB package...${NC}"
dpkg-deb --build "${DEB_DIR}"

echo -e "${YELLOW}Generating MD5 checksum...${NC}"
md5sum "${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb" > "${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb.md5"

rm -rf "${BUILD_DIR}/temp_clone"
rm -rf "${DEB_DIR}"

echo -e "${GREEN}✓ Package built successfully!${NC}"
echo ""
echo -e "${GREEN}Package information:${NC}"
echo "  Name: ${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo "  Location: ${BUILD_DIR}/"
echo "  Size: $(du -h ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb | cut -f1)"
echo "  MD5:  $(cat ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb.md5)"
echo ""
echo -e "${GREEN}To install the package, run:${NC}"
echo "  sudo dpkg -i ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo ""
echo -e "${GREEN}Or with apt to handle dependencies:${NC}"
echo "  sudo apt install ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo ""
echo -e "${GREEN}To remove the package:${NC}"
echo "  sudo apt remove ${PACKAGE_NAME}"
echo ""
echo -e "${GREEN}To completely purge (including data):${NC}"
echo "  sudo apt purge ${PACKAGE_NAME}"