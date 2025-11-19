FROM ros:humble-perception

ENV WS_DIR="/ros2_ws"
ENV EXPORT_DIR="/export"

SHELL ["/bin/bash", "-c"]

ARG DEBIAN_FRONTEND=noninteractive
ARG UID=1000
ARG GID=1000
ARG UNAME=user
ARG ROS_DOMAIN_ID=42

# === Base setup ===
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git-all \
    nano \
    python3-tk \
    software-properties-common \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# === Add ROS workspace and source code ===
WORKDIR ${WS_DIR}
RUN mkdir -p $WS_DIR/src

COPY ros2_ws/src/ $WS_DIR/src/

# === Install ui dependencies ===
RUN apt-get update && apt-get install -y \
    python3-pyqt5 \
    && pip install --upgrade pip \
    && pip uninstall -y numpy opencv-python opencv-python-headless opencv-contrib-python || true \
    && pip install "numpy>=1.21.0,<2.0" \
    && pip install opencv-python-headless==4.8.1.78 \
    && pip install matplotlib




# === Add user ===
RUN groupadd -g ${GID} ${UNAME} || true \
 && useradd -m -u ${UID} -g ${GID} -s /bin/bash ${UNAME} || true \
 && usermod -aG sudo ${UNAME} \
 && echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
 && mkdir -p /home/${UNAME}/.ros/log && \
    chown -R ${UID}:${GID} /home/${UNAME}/.ros


# === Setup VScapture path ===
RUN apt-get update && \
    apt-get install -y dotnet-runtime-8.0
COPY VSCaptureCLIv1.006Binary /opt/vscapture/VSCaptureCLIv1.006Binary
RUN chmod +x /opt/vscapture/VSCaptureCLIv1.006Binary/VSCaptureCLI.dll 

# === Add VSCapture Wrapper Script ===
# COPY the wrapper script from your build context to a PATH location
COPY ros2_ws/src/vital_recording/run_vscapture.sh /usr/local/bin/
# Make it executable
RUN chmod +x /usr/local/bin/run_vscapture.sh

# === Update VSCapture environment variable ===
ENV VSCAPTURE_PATH="/opt/vscapture/VSCaptureCLIv1.006Binary"


# === Setup ROS workspace ===
USER ${UNAME}
RUN sudo chown -R ${UID}:${GID} ${WS_DIR} ${EXPORT_DIR} || true

RUN cd ${WS_DIR} && \
    source /opt/ros/${ROS_DISTRO}/setup.bash && \
    rosdep update && \
    rosdep install --from-paths src --ignore-src -r -y && \
    colcon build --symlink-install

# === Setup environment ===
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc && \
    echo "source ${WS_DIR}/install/setup.bash" >> ~/.bashrc && \
    echo "export ROS_DOMAIN_ID=${ROS_DOMAIN_ID}" >> ~/.bashrc && \
    echo "export DISPLAY=:0" >> ~/.bashrc && \
    echo "export XDG_RUNTIME_DIR=/tmp/runtime-${UID}" >> ~/.bashrc

# === Create runtime and ros log directory ===
RUN mkdir -p /tmp/runtime-${UID} && \
    mkdir -p /home/${UNAME}/.ros/log && \
    sudo chown -R ${UID}:${GID} /tmp/runtime-${UID} /home/${UNAME}/.ros

ENV HOME=/home/${UNAME}

WORKDIR ${WS_DIR}


