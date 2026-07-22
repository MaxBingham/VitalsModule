FROM ros:humble-ros-base

ENV WS_DIR="/ros2_ws"
ENV EXPORT_DIR="/export"
SHELL ["/bin/bash", "-c"]

ARG DEBIAN_FRONTEND=noninteractive
ARG UID=1000
ARG GID=1000
ARG UNAME=user

# === Base setup ===
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git-all \
    nano \
    netcat-openbsd \
    python3-tk \
    python3-pip \
    software-properties-common \
    sudo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/archives/*

# === Add user (as root) ===
RUN groupadd -g ${GID} ${UNAME} \
 && useradd -m -u ${UID} -g ${GID} -s /bin/bash ${UNAME} \
 && echo "${UNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${UNAME} \
 && chmod 0440 /etc/sudoers.d/${UNAME} \
 && usermod -a -G dialout,tty ${UNAME}

# === Setup ROS workspace structure (as root) ===
RUN mkdir -p ${WS_DIR}/src ${EXPORT_DIR} /tmp/runtime-${UID}
WORKDIR ${WS_DIR}

# Copy source code after directory is created
RUN mkdir -p src 
COPY ros2_ws/src/ ./src/

# IMPORTANT: Set correct ownership for the non-root user
RUN chown -R ${UID}:${GID} ${WS_DIR} ${EXPORT_DIR} /tmp/runtime-${UID} \
 && mkdir -p /home/${UNAME}/.ros/log \
 && chown -R ${UID}:${GID} /home/${UNAME}/.ros


# === Install ui dependencies ===
RUN pip3 install matplotlib


# === Setup VScapture path ===
RUN apt-get update && \
    apt-get install -y dotnet-runtime-8.0 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /var/cache/apt/archives/*
COPY VSCaptureCLIv1.006Binary /opt/vscapture/VSCaptureCLIv1.006Binary
RUN chmod +x /opt/vscapture/VSCaptureCLIv1.006Binary/VSCaptureCLI.dll \
 && chown -R ${UID}:${GID} /opt/vscapture 

# === Add VSCapture Wrapper Script ===
# COPY the wrapper script from your build context to a PATH location
COPY ros2_ws/src/vital_recording/run_vscapture.sh /usr/local/bin/
# Make it executable
RUN chmod +x /usr/local/bin/run_vscapture.sh

# === Add container startup script ===
COPY docker/container-startup.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/container-startup.sh

# === Add functionality check script for container healthcheck ===
COPY docker/functionality_check.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/functionality_check.sh

# === Update VSCapture environment variable ===
ENV VSCAPTURE_PATH="/opt/vscapture/VSCaptureCLIv1.006Binary"

# === Install rqt for ros-humble ===
RUN apt update && apt install -y \
    ros-humble-rqt-graph \
    ros-humble-rqt \
    ros-humble-rqt-gui \
    ros-humble-rqt-gui-py \
    graphviz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /var/cache/apt/archives/*

# === Install Foxglove Bridge === #To Do: Split into two images
RUN apt-get update && apt-get install -y \
    ros-humble-foxglove-bridge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# === Setup ROS workspace (as non-root user) ===
USER ${UNAME}
WORKDIR ${WS_DIR}


RUN source /opt/ros/${ROS_DISTRO}/setup.bash && \
    rosdep update && \
    rosdep install --from-paths src --ignore-src -r -y && \
    colcon build --symlink-install

# === Setup environment (as non-root user) ===
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc && \
    echo "source ${WS_DIR}/install/setup.bash" >> ~/.bashrc && \
    echo "export DISPLAY=:0" >> ~/.bashrc && \
    echo "export XDG_RUNTIME_DIR=/tmp/runtime-${UID}" >> ~/.bashrc

ENV HOME=/home/${UNAME}

# Use a startup script to handle permissions and environment setup
CMD ["/usr/local/bin/container-startup.sh"]


