# Hypervisor Using KVM/QEMU

A Type-2 hypervisor for Linux systems using **libvirt** to manage **KVM/QEMU** virtual machines (VMs). This project includes two interfaces:

- **Command Line Interface (CLI)**: Written in C++ for VM management.
- **Graphical User Interface (GUI)**: Built with Python's Tkinter, offering an enhanced user experience with advanced features like VirtIO driver support, network selection, and VNC console access.

> **Note:** This project requires a Linux OS and has been tested on **Ubuntu 24.04**.

---

## Features

- **List VMs**: Display all active and inactive VMs with details (name, status, ID, memory, vCPUs, autostart).
- **Create VMs**: From ISO with customizable memory, vCPUs, disk size, and network. GUI supports VirtIO for Windows.
- **Start/Restart VMs**
- **Delete VMs**: Optionally delete associated disk images.
- **VNC Console Access**: GUI access to VM via VNC viewer.
- **Network Selection**: Choose libvirt networks in GUI.
- **Activity Log**: Real-time logs with timestamps (GUI).
- **Theming**: GUI theme switching.

---

## Prerequisites

- **Operating System**: Linux (tested on Ubuntu 24.04)
- **Hypervisor**: KVM/QEMU with libvirt , TigerVNC 
- **Root Privileges**: Use `sudo` or be in `libvirt` group

### Dependencies

#### CLI:
- `libvirt-dev`
- `g++`
- `qemu-img`

#### GUI:
- `python3`
- `python3-tk`
- `libvirt-python`
- `python-slugify`
- `vncviewer`

> **VirtIO Drivers**: Needed for Windows VMs 

---

## Installation

### 1. Install System Dependencies

```bash
sudo apt update
sudo apt install -y libvirt-dev g++ qemu-kvm libvirt-daemon-system python3 python3-pip python3-tk virt-viewer
pip install -r requirements.txt
```

### 2. Clone the Repository

```bash
git clone https://github.com/NRNarender/Hypervisor.git
cd Hypervisor
```

### 3. Compile the CLI

```bash
g++ -o hypervisor Hypervisor_CLI.cpp -lvirt
```

### 4. Set Up Permissions

```bash
sudo usermod -aG libvirt $USER
```

> Log out and log back in for changes to apply.

### 5. Verify KVM/QEMU Setup

```bash
sudo systemctl enable --now libvirtd
kvm-ok
```

### 6. Download ISO Files

- **Windows ISO**: Download from Microsoft.
- **Ubuntu ISO**: Download from Ubuntu. (or any other Operating System)
- **VirtIO ISO**: Download from Fedora (e.g., `virtio-win.iso`).
- Place them in `/var/lib/libvirt/images/`.

---

## Usage

### CLI

Run:

```bash
sudo ./hypervisor
```

#### Menu Options:

1. List all VMs  
2. Create a new VM from ISO  
3. Start a VM  
4. Stop a VM (graceful)  
5. Force stop a VM  
6. Delete a VM  
7. Exit  

#### Example (Create a VM):

- Select option `2` to create a VM.
- Enter VM name (e.g., `test`).
- Enter ISO path (e.g., `/var/lib/libvirt/images/windows.iso`).
- Enter VirtIO ISO path (e.g., `/var/lib/libvirt/images/virtio-win.iso`).
- Specify memory (e.g., `2048 MB`), vCPUs (e.g., `2`), and disk size (e.g., `20 GB`).
- Select option `3` to start the VM (e.g., `test`).
- Find the VNC port number:
```bash
virsh dumpxml VM_NAME | grep vnc
```
- Connect to the VM using TigerVNC:
```bash
vncviewer localhost:PORT_NO   
```
**Note:** Port `5900` is the default for the first VM; subsequent VMs may use `5901`, `5902`, etc.

---

### GUI

Run:

```bash
sudo python3 Hypervisor_GUI.py
```

#### Tabs:

1. **Virtual Machines**: View and manage VMs, open VNC.
2. **Create VM**:
   - Enter VM name
   - Path to Windows ISO
   - Path to VirtIO ISO
   - Memory, vCPUs, Disk size
   - Select libvirt network (optional)
3. **Settings**: Change theme, URI, toggle log timestamps.

---


## VNC Console

- Select running VM
- Click **Deploy**
- Launches `vncviewer` for graphical access

---

## Notes

- **Disk Images**: Stored in `/var/lib/libvirt/images/`
- **VNC**: Uses `virt-viewer` or compatible client
- **Permissions**: Ensure write access to libvirt image directory
- **VirtIO**: Needed for Windows Installation
- **Network**: CLI uses default; GUI allows custom selection

---

