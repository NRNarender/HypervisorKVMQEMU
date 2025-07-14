#include <iostream>
#include <string>
#include <vector>
#include <libvirt/libvirt.h>
#include <memory>
#include <fstream>
#include <unistd.h>

using namespace std;

void listAllVMs(virConnectPtr conn) {
    int numActiveDomains = virConnectNumOfDomains(conn);
    vector<int> activeDomains(numActiveDomains);
    virConnectListDomains(conn, activeDomains.data(), numActiveDomains);
    int numInactiveDomains = virConnectNumOfDefinedDomains(conn);
    vector<char*> inactiveDomains(numInactiveDomains);
    virConnectListDefinedDomains(conn, inactiveDomains.data(), numInactiveDomains);
    cout << "VMs:" << endl;
    cout << "===== ACTIVE VMs =====" << endl;
    for (int i = 0; i < numActiveDomains; i++) {
        virDomainPtr dom = virDomainLookupByID(conn, activeDomains[i]);
        if (dom) {
            cout << "- " << virDomainGetName(dom) << " (ID: " << activeDomains[i] << ")" << endl;
            virDomainFree(dom);
        }
    }
    cout << "===== INACTIVE VMs =====" << endl;
    for (int i = 0; i < numInactiveDomains; i++) {
        cout << "- " << inactiveDomains[i] << " (Inactive)" << endl;
        free(inactiveDomains[i]);
    }
}

bool startVM(virConnectPtr conn, const char* vmName) {
    virDomainPtr dom = virDomainLookupByName(conn, vmName);
    if (!dom) {
        cerr << "Error: VM '" << vmName << "' not found!" << endl;
        return false;
    }
    int result = virDomainCreate(dom);
    if (result < 0) {
        cerr << "Error: Failed to start VM '" << vmName << "'" << endl;
        virDomainFree(dom);
        return false;
    }
    cout << "VM '" << vmName << "' started successfully" << endl;
    virDomainFree(dom);
    return true;
}

bool stopVM(virConnectPtr conn, const char* vmName) {
    virDomainPtr dom = virDomainLookupByName(conn, vmName);
    if (!dom) {
        cerr << "Error: VM '" << vmName << "' not found!" << endl;
        return false;
    }
    int result = virDomainShutdown(dom);
    if (result < 0) {
        cerr << "Error: Failed to stop VM '" << vmName << "'" << endl;
        virDomainFree(dom);
        return false;
    }
    cout << "VM '" << vmName << "' is shutting down..." << endl;
    virDomainFree(dom);
    return true;
}

bool forceStopVM(virConnectPtr conn, const char* vmName) {
    virDomainPtr dom = virDomainLookupByName(conn, vmName);
    if (!dom) {
        cerr << "Error: VM '" << vmName << "' not found!" << endl;
        return false;
    }
    int result = virDomainDestroy(dom);
    if (result < 0) {
        cerr << "Error: Failed to force stop VM '" << vmName << "'" << endl;
        virDomainFree(dom);
        return false;
    }
    cout << "VM '" << vmName << "' forcibly stopped" << endl;
    virDomainFree(dom);
    return true;
}

bool createVM(virConnectPtr conn, const string& vmName, const string& isoPath, 
              const string& virtioPath, int memoryMB = 2048, int vcpus = 2, int diskGB = 20) {
    ifstream isoFile(isoPath);
    if (!isoFile.good()) {
        cerr << "Error: ISO file '" << isoPath << "' does not exist!" << endl;
        return false;
    }
    ifstream virtioFile(virtioPath);
    if (!virtioFile.good()) {
        cerr << "Error: VirtIO ISO file '" << virtioPath << "' does not exist!" << endl;
        return false;
    }
    string diskPath = "/var/lib/libvirt/images/" + vmName + ".qcow2";
    string createDiskCmd = "qemu-img create -f qcow2 " + diskPath + " " + to_string(diskGB) + "G";
    cout << "Creating disk image..." << endl;
    int ret = system(createDiskCmd.c_str());
    if (ret != 0) {
        cerr << "Error: Failed to create disk image!" << endl;
        return false;
    }
    string xmlConfig = "<?xml version='1.0' encoding='UTF-8'?>\n"
                       "<domain type='kvm'>\n"
                       "  <name>" + vmName + "</name>\n"
                       "  <memory unit='KiB'>" + to_string(memoryMB * 1024) + "</memory>\n"
                       "  <vcpu>" + to_string(vcpus) + "</vcpu>\n"
                       "  <os>\n"
                       "    <type arch='x86_64'>hvm</type>\n"
                       "    <boot dev='cdrom'/>\n"
                       "    <boot dev='hd'/>\n"
                       "  </os>\n"
                       "  <features>\n"
                       "    <acpi/>\n"
                       "    <apic/>\n"
                       "    <vmport state='off'/>\n"
                       "  </features>\n"
                       "  <cpu mode='host-passthrough'/>\n"
                       "  <clock offset='localtime'/>\n"
                       "  <devices>\n"
                       "    <disk type='file' device='disk'>\n"
                       "      <driver name='qemu' type='qcow2'/>\n"
                       "      <source file='" + diskPath + "'/>\n"
                       "      <target dev='vda' bus='virtio'/>\n"
                       "      <address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>\n"
                       "    </disk>\n"
                       "    <disk type='file' device='cdrom'>\n"
                       "      <driver name='qemu' type='raw'/>\n"
                       "      <source file='" + isoPath + "'/>\n"
                       "      <target dev='sda' bus='sata'/>\n"
                       "      <readonly/>\n"
                       "      <address type='drive' controller='0' bus='0' target='0' unit='0'/>\n"
                       "    </disk>\n"
                       "    <disk type='file' device='cdrom'>\n"
                       "      <driver name='qemu' type='raw'/>\n"
                       "      <source file='" + virtioPath + "'/>\n"
                       "      <target dev='sdb' bus='sata'/>\n"
                       "      <readonly/>\n"
                       "      <address type='drive' controller='0' bus='0' target='0' unit='1'/>\n"
                       "    </disk>\n"
                       "    <controller type='sata' index='0'>\n"
                       "      <address type='pci' domain='0x0000' bus='0x00' slot='0x05' function='0x0'/>\n"
                       "    </controller>\n"
                       "    <interface type='network'>\n"
                       "      <source network='default'/>\n"
                       "      <model type='virtio'/>\n"
                       "      <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>\n"
                       "    </interface>\n"
                       "    <graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'/>\n"
                       "    <video>\n"
                       "      <model type='virtio'/>\n"
                       "      <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0'/>\n"
                       "    </video>\n"
                       "    <input type='tablet' bus='usb'/>\n"
                       "    <input type='keyboard' bus='ps2'/>\n"
                       "    <input type='mouse' bus='ps2'/>\n"
                       "    <controller type='usb' index='0' model='ich9-ehci1'/>\n"
                       "    <controller type='pci' index='0' model='pci-root'/>\n"
                       "  </devices>\n"
                       "</domain>";
    virDomainPtr dom = virDomainDefineXML(conn, xmlConfig.c_str());
    if (!dom) {
        cerr << "Error: Failed to define VM!" << endl;
        unlink(diskPath.c_str());
        return false;
    }
    cout << "VM '" << vmName << "' created successfully" << endl;
    cout << "- Memory: " << memoryMB << " MB" << endl;
    cout << "- vCPUs: " << vcpus << endl;
    cout << "- Disk: " << diskGB << " GB" << endl;
    cout << "- ISO: " << isoPath << endl;
    cout << "- VirtIO ISO: " << virtioPath << endl;
    cout << "- VNC: Enabled (connect to this host to access)" << endl;
    cout << "To install Windows: In the Windows installer, click 'Load driver', "
         << "select the VirtIO CDROM, and navigate to 'vioscsi\\<WindowsVersion>\\amd64' "
         << "(e.g., 'vioscsi\\w10\\amd64' for Windows 10 64-bit)." << endl;
    virDomainFree(dom);
    return true;
}

bool deleteVM(virConnectPtr conn, const char* vmName) {
    virDomainPtr dom = virDomainLookupByName(conn, vmName);
    if (!dom) {
        cerr << "Error: VM '" << vmName << "' not found!" << endl;
        return false;
    }
    int isActive = virDomainIsActive(dom);
    if (isActive == 1) {
        cout << "VM is active. Stopping it first..." << endl;
        virDomainDestroy(dom);
    }
    char *xmlDesc = virDomainGetXMLDesc(dom, 0);
    string xml(xmlDesc);
    free(xmlDesc);
    size_t diskPos = xml.find("<source file='");
    string diskPath;
    if (diskPos != string::npos) {
        diskPos += 14;
        size_t endPos = xml.find("'", diskPos);
        if (endPos != string::npos) {
            diskPath = xml.substr(diskPos, endPos - diskPos);
        }
    }
    int result = virDomainUndefine(dom);
    virDomainFree(dom);
    if (result < 0) {
        cerr << "Error: Failed to undefine VM '" << vmName << "'" << endl;
        return false;
    }
    if (!diskPath.empty() && diskPath.find("/var/lib/libvirt/images/") == 0) {
        cout << "Deleting disk file: " << diskPath << endl;
        unlink(diskPath.c_str());
    }
    cout << "VM '" << vmName << "' deleted successfully" << endl;
    return true;
}

int main() {
    virConnectPtr conn = virConnectOpen("qemu:///system");
    if (!conn) {
        cerr << "Failed to connect to hypervisor!" << endl;
        return 1;
    }
    cout << "=== Narender's Project - Hypervisor ===" << endl;
    bool running = true;
    while (running) {
        cout << "\nOptions:" << endl;
        cout << "1. List all VMs" << endl;
        cout << "2. Create a new VM from ISO" << endl;
        cout << "3. Start a VM" << endl;
        cout << "4. Stop a VM (graceful)" << endl;
        cout << "5. Force stop a VM" << endl;
        cout << "6. Delete a VM" << endl;
        cout << "0. Exit" << endl;
        cout << endl;
        cout << "Enter your choice: ";
        int choice;
        cin >> choice;
        cin.ignore();
        string vmName, isoPath, virtioPath;
        int memoryMB, vcpus, diskGB;
        switch (choice) {
            case 1:
                listAllVMs(conn);
                break;
            case 2:
                cout << "Enter VM name: ";
                getline(cin, vmName);
                cout << "Enter ISO file path: ";
                getline(cin, isoPath);
                cout << "Enter VirtIO ISO file path: ";
                getline(cin, virtioPath);
                cout << "Enter memory size (MB, default 2048): ";
                cin >> memoryMB;
                if (memoryMB <= 0) memoryMB = 2048;
                cout << "Enter number of vCPUs (default 2): ";
                cin >> vcpus;
                if (vcpus <= 0) vcpus = 2;
                cout << "Enter disk size (GB, default 20): ";
                cin >> diskGB;
                if (diskGB <= 0) diskGB = 20;
                createVM(conn, vmName, isoPath, virtioPath, memoryMB, vcpus, diskGB);
                break;
            case 3:
                cout << "Enter VM name to start: ";
                getline(cin, vmName);
                startVM(conn, vmName.c_str());
                break;
            case 4:
                cout << "Enter VM name to stop: ";
                getline(cin, vmName);
                stopVM(conn, vmName.c_str());
                break;
            case 5:
                cout << "Enter VM name to force stop: ";
                getline(cin, vmName);
                forceStopVM(conn, vmName.c_str());
                break;
            case 6:
                cout << "Enter VM name to delete: ";
                getline(cin, vmName);
                deleteVM(conn, vmName.c_str());
                break;
            case 0:
                running = false;
                break;
            default:
                cout << "Invalid choice. Please try again." << endl;
        }
    }
    virConnectClose(conn);
    return 0;
}