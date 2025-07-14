import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import os
import libvirt
import threading
from datetime import datetime
import xml.etree.ElementTree as ET
import logging
import re
import time
from slugify import slugify

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind('<Enter>', self.show_tip)
        widget.bind('<Leave>', self.hide_tip)

    def show_tip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self.tip_window, text=self.text, background="#ffffe0",
                          relief=tk.SOLID, borderwidth=1, padding=5)
        label.pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
        self.tip_window = None

class EnhancedHypervisorManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Narender's Project - Hypervisor ")
        self.root.geometry("1000x700")
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, 
                                   anchor=tk.W, style='Status.TLabel')
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.connection_status = tk.StringVar()
        self.connection_status.set("Connecting...")
        self.conn = None
        self.connect_to_hypervisor()
        self.init_ui()
        self.refresh_vm_list()

    def configure_styles(self):
        self.style.configure('TButton', padding=5)
        self.style.configure('Title.TLabel', font=('Helvetica', 12, 'bold'))
        self.style.configure('Status.TLabel', font=('Helvetica', 10))
        self.style.configure('Treeview', rowheight=25)
        self.style.configure('Treeview.Heading', font=('Helvetica', 9, 'bold'))
        self.style.map('Treeview', background=[('selected', '#347083')])
        self.style.configure('Error.TLabel', foreground='red')
        self.style.configure('Accent.TButton', foreground='white', background='#305680')

    def connect_to_hypervisor(self):
        def connect_thread():
            try:
                self.conn = libvirt.open("qemu:///system")
                if self.conn:
                    self.root.after(0, lambda: self.connection_status.set(f"Connected to {self.conn.getHostname()}"))
                    logging.info("Connected to hypervisor")
                else:
                    self.root.after(0, lambda: self.connection_status.set("Not connected"))
                    logging.error("Failed to connect to hypervisor")
            except libvirt.libvirtError as e:
                self.root.after(0, lambda: self.connection_status.set("Connection failed"))
                logging.error(f"Connection error: {e}")
        threading.Thread(target=connect_thread).start()

    def init_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        vm_list_frame = ttk.Frame(notebook)
        notebook.add(vm_list_frame, text="Virtual Machines")
        self.setup_vm_list_tab(vm_list_frame)
        create_vm_frame = ttk.Frame(notebook)
        notebook.add(create_vm_frame, text="Create VM")
        self.setup_create_vm_tab(create_vm_frame)
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Settings")
        self.setup_settings_tab(settings_frame)
        console_frame = ttk.LabelFrame(self.root, text="Activity Log")
        console_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.console = scrolledtext.ScrolledText(console_frame, height=8, wrap=tk.WORD)
        self.console.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.console.config(state=tk.DISABLED)
        self.console.tag_config('error', foreground='red')
        self.log_to_console(f"Application started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def setup_vm_list_tab(self, parent):
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(header_frame, text="Virtual Machine Manager", style='Title.TLabel').pack(side=tk.LEFT)
        ttk.Label(header_frame, textvariable=self.connection_status, style='Installer.TLabel').pack(side=tk.RIGHT)
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        columns = ('name', 'status', 'id', 'memory', 'vcpu', 'autostart')
        self.vm_tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        self.vm_tree.heading('name', text='VM Name')
        self.vm_tree.heading('status', text='Status')
        self.vm_tree.heading('id', text='ID')
        self.vm_tree.heading('memory', text='Memory (MB)')
        self.vm_tree.heading('vcpu', text='vCPUs')
        self.vm_tree.heading('autostart', text='Autostart')
        self.vm_tree.column('name', width=200, anchor=tk.W)
        self.vm_tree.column('status', width=100, anchor=tk.CENTER)
        self.vm_tree.column('id', width=50, anchor=tk.CENTER)
        self.vm_tree.column('memory', width=100, anchor=tk.CENTER)
        self.vm_tree.column('vcpu', width=70, anchor=tk.CENTER)
        self.vm_tree.column('autostart', width=80, anchor=tk.CENTER)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.vm_tree.yview)
        self.vm_tree.configure(yscroll=scrollbar.set)
        self.vm_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.vm_tree.bind('<Double-1>', self.show_vm_details)
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        controls = [
            ("Refresh", self.refresh_vm_list, 'Accent.TButton'),
            ("Start VM", self.start_vm),
            ("Restart VM", self.restart_vm),
            ("VM Details", self.show_vm_details),
            ("Delete VM", self.delete_vm),
            ("Deploy", self.open_console),
        ]
        for i, (text, command, *style) in enumerate(controls):
            btn = ttk.Button(btn_frame, text=text, command=command, style=style[0] if style else None)
            btn.pack(side=tk.LEFT, padx=5, pady=2)
            if i == 2: 
                ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

    def setup_create_vm_tab(self, parent):
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        ttk.Label(form_frame, text="Create New Virtual Machine", style='Title.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 15))
        ttk.Label(form_frame, text="VM Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.vm_name_entry = ttk.Entry(form_frame, width=40)
        self.vm_name_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        Tooltip(self.vm_name_entry, "Enter a unique VM name (letters, numbers, underscores, hyphens)")
        iso_frame = ttk.Frame(form_frame)
        iso_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        ttk.Label(iso_frame, text="Windows ISO:").pack(side=tk.LEFT)
        self.iso_path_entry = ttk.Entry(iso_frame, width=50)
        self.iso_path_entry.pack(side=tk.LEFT, padx=5)
        Tooltip(self.iso_path_entry, "Select a Windows ISO image for installation")
        ttk.Button(iso_frame, text="Browse...", command=self.browse_iso).pack(side=tk.LEFT)
        self.iso_path = "/var/lib/libvirt/images/Windows.iso"  
        self.iso_path_entry.insert(0, self.iso_path)
        virtio_frame = ttk.Frame(form_frame)
        virtio_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        ttk.Label(virtio_frame, text="VirtIO ISO:").pack(side=tk.LEFT)
        self.virtio_path_entry = ttk.Entry(virtio_frame, width=50)
        self.virtio_path_entry.pack(side=tk.LEFT, padx=5)
        Tooltip(self.virtio_path_entry, "Select the VirtIO driver ISO (e.g., virtio-win.iso)")
        ttk.Button(virtio_frame, text="Browse...", command=self.browse_virtio).pack(side=tk.LEFT)
        self.virtio_path = "/var/lib/libvirt/images/virtio-win.iso"  
        self.virtio_path_entry.insert(0, self.virtio_path)
        resource_frame = ttk.LabelFrame(form_frame, text="Resource Allocation")
        resource_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W+tk.E, pady=10, padx=5)
        entries = [
            ("Memory (MB):", "memory_entry", "2048"),
            ("vCPUs:", "vcpu_entry", "2"),
            ("Disk Size (GB):", "disk_entry", "20")
        ]
        for i, (label, attr, default) in enumerate(entries):
            ttk.Label(resource_frame, text=label).grid(row=0, column=i*2, sticky=tk.W, pady=5, padx=5)
            entry = ttk.Entry(resource_frame, width=10)
            entry.insert(0, default)
            entry.grid(row=0, column=i*2+1, sticky=tk.W, pady=5, padx=5)
            setattr(self, attr, entry)
            Tooltip(entry, f"Enter {label.split(':')[0].lower()} (must be positive integer)")
        network_frame = ttk.LabelFrame(form_frame, text="Network Settings")
        network_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W+tk.E, pady=10, padx=5)
        ttk.Label(network_frame, text="Network:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.network_combo = ttk.Combobox(network_frame, state="readonly")
        self.load_available_networks()
        Tooltip(self.network_combo, "Select network type for the VM")
        create_btn_frame = ttk.Frame(form_frame)
        create_btn_frame.grid(row=6, column=0, columnspan=2, pady=20)
        self.create_btn = ttk.Button(create_btn_frame, text="Create VM", command=self.create_vm, style='Accent.TButton')
        self.create_btn.pack(pady=10, ipadx=20, ipady=5)
        self.progress_bar = ttk.Progressbar(form_frame, mode='indeterminate')
        self.progress_bar.grid(row=7, column=0, columnspan=2, sticky=tk.W+tk.E, pady=5)

    def load_available_networks(self):
        try:
            if self.conn and self.conn.isAlive():
                active_nets = self.conn.listNetworks()
                inactive_nets = self.conn.listDefinedNetworks()
                networks = active_nets + inactive_nets
                if not networks:
                    networks = ["default"]
                    self.log_to_console("No networks available, using default", error=True)
                self.network_combo['values'] = networks
                if networks:
                    self.network_combo.set(networks[0])
            else:
                self.network_combo['values'] = ["default"]
                self.network_combo.set("default")
                self.log_to_console("Connection not available, using default network", error=True)
        except libvirt.libvirtError as e:
            self.log_to_console(f"Error loading networks: {e}", error=True)
            self.network_combo['values'] = ["default"]
            self.network_combo.set("default")

    def setup_settings_tab(self, parent):
        settings_frame = ttk.Frame(parent)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        ttk.Label(settings_frame, text="Application Settings", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 15))
        theme_frame = ttk.Frame(settings_frame)
        theme_frame.pack(fill=tk.X, pady=5)
        ttk.Label(theme_frame, text="Theme:").pack(side=tk.LEFT)
        self.theme_var = tk.StringVar()
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var, 
                                  values=['clam', 'alt', 'default', 'classic'], state='readonly')
        theme_combo.set('clam')
        theme_combo.pack(side=tk.LEFT, padx=5)
        theme_combo.bind('<<ComboboxSelected>>', self.change_theme)
        log_frame = ttk.Frame(settings_frame)
        log_frame.pack(fill=tk.X, pady=5)
        self.timestamp_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(log_frame, text="Show timestamps in log", variable=self.timestamp_var).pack(anchor=tk.W)
        conn_frame = ttk.LabelFrame(settings_frame, text="Hypervisor Connection")
        conn_frame.pack(fill=tk.X, pady=10)
        ttk.Label(conn_frame, text="URI:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.uri_entry = ttk.Entry(conn_frame)
        self.uri_entry.insert(0, "qemu:///system")
        self.uri_entry.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5, padx=5)
        ttk.Button(conn_frame, text="Reconnect", command=self.reconnect_hypervisor).grid(row=0, column=2, padx=5)

    def ensure_connection(self):
        if not self.conn or not self.conn.isAlive():
            self.log_to_console("Connection lost, attempting to reconnect...", error=True)
            self.reconnect_hypervisor()
            return False
        return True

    def change_theme(self, event=None):
        self.style.theme_use(self.theme_var.get())

    def reconnect_hypervisor(self):
        uri = self.uri_entry.get()
        def reconnect_thread():
            try:
                if self.conn:
                    self.conn.close()
                self.conn = libvirt.open(uri)
                if self.conn:
                    self.root.after(0, lambda: self.connection_status.set(f"Connected to {self.conn.getHostname()}"))
                    self.log_to_console(f"Reconnected to {uri}")
                    self.load_available_networks()
                    self.refresh_vm_list()
                else:
                    self.root.after(0, lambda: self.connection_status.set("Connection failed"))
                    self.log_to_console("Reconnection failed", error=True)
            except libvirt.libvirtError as e:
                self.root.after(0, lambda: self.connection_status.set("Connection failed"))
                self.log_to_console(f"Reconnection error: {e}", error=True)
        threading.Thread(target=reconnect_thread).start()

    def show_vm_details(self, event=None):
        if not self.ensure_connection():
            return
        selected_item = self.vm_tree.focus()
        values = self.vm_tree.item(selected_item, 'values')
        if values:
            vm_name = values[0]
            try:
                dom = self.conn.lookupByName(vm_name)
                xml_desc = dom.XMLDesc(0)
                root = ET.fromstring(xml_desc)
                details = [
                    f"Name: {vm_name}",
                    f"Status: {values[1]}",
                    f"Memory: {values[3]} MB",
                    f"vCPUs: {values[4]}",
                    f"Autostart: {values[5]}",
                    f"UUID: {dom.UUIDString()}",
                    f"OSType: {root.find('./os/type').get('arch')}"
                ]
                messagebox.showinfo("VM Details", "\n".join(details))
            except libvirt.libvirtError as e:
                self.log_to_console(f"Error getting VM details: {e}", error=True)

    def browse_iso(self):
        filename = filedialog.askopenfilename(
            title="Select Windows ISO file",
            filetypes=(("ISO files", "*.iso"), ("All files", "*.*"))
        )
        if filename:
            self.iso_path_entry.delete(0, tk.END)
            self.iso_path_entry.insert(0, filename)
            self.iso_path = filename

    def browse_virtio(self):
        filename = filedialog.askopenfilename(
            title="Select VirtIO ISO file",
            filetypes=(("ISO files", "*.iso"), ("All files", "*.*"))
        )
        if filename:
            self.virtio_path_entry.delete(0, tk.END)
            self.virtio_path_entry.insert(0, filename)
            self.virtio_path = filename

    def log_to_console(self, message, error=False):
        def update_console():
            timestamp = datetime.now().strftime('%H:%M:%S') if self.timestamp_var.get() else ""
            log_message = f"[{timestamp}] {message}" if timestamp else message
            self.console.config(state=tk.NORMAL)
            self.console.insert(tk.END, log_message + "\n", 'error' if error else '')
            self.console.see(tk.END)
            self.console.config(state=tk.DISABLED)
            self.status_var.set(message[:100])
        self.root.after(0, update_console)

    def refresh_vm_list(self):
        if not self.ensure_connection():
            return
        for item in self.vm_tree.get_children():
            self.vm_tree.delete(item)
        try:
            all_domains = []
            try:
                active_ids = self.conn.listDomainsID()
                for dom_id in active_ids:
                    try:
                        dom = self.conn.lookupByID(dom_id)
                        all_domains.append((dom, True))
                    except libvirt.libvirtError as e:
                        self.log_to_console(f"Error looking up domain ID {dom_id}: {e}", error=True)
            except libvirt.libvirtError as e:
                self.log_to_console(f"Error listing active domains: {e}", error=True)
            try:
                inactive_names = self.conn.listDefinedDomains()
                for name in inactive_names:
                    try:
                        dom = self.conn.lookupByName(name)
                        all_domains.append((dom, False))
                    except libvirt.libvirtError as e:
                        self.log_to_console(f"Error looking up domain name {name}: {e}", error=True)
            except libvirt.libvirtError as e:
                self.log_to_console(f"Error listing inactive domains: {e}", error=True)
            inactive_counter = 1000
            for dom, is_active in all_domains:
                try:
                    name = dom.name()
                    autostart = dom.autostart()
                    dom_id = dom.ID() if is_active else inactive_counter
                    if not is_active:
                        inactive_counter += 1
                    self.vm_tree.insert('', tk.END, values=(
                        name, 
                        "Running" if is_active else "Stopped", 
                        dom_id, 
                        dom.maxMemory() // 1024,
                        dom.maxVcpus(),
                        "Yes" if autostart else "No"
                    ))
                except libvirt.libvirtError as e:
                    self.log_to_console(f"Error processing domain {dom.name() if hasattr(dom, 'name') else 'unknown'}: {e}", error=True)
            self.log_to_console("VM list refreshed successfully")
        except libvirt.libvirtError as e:
            self.log_to_console(f"Error refreshing VM list: {e}", error=True)

    def get_selected_vm(self):
        selected_items = self.vm_tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select a VM from the list.")
            return None
        return self.vm_tree.item(selected_items[0])['values'][0]

    def start_vm(self):
        if not self.ensure_connection():
            return
        vm_name = self.get_selected_vm()
        if not vm_name:
            return
        def start_thread():
            try:
                dom = self.conn.lookupByName(vm_name)
                if dom.isActive():
                    self.log_to_console(f"VM '{vm_name}' is already running")
                    return
                dom.create()
                self.log_to_console(f"VM '{vm_name}' started")
                self.refresh_vm_list()
            except libvirt.libvirtError as e:
                self.log_to_console(f"Error starting VM: {e}", error=True)
        threading.Thread(target=start_thread).start()

    def restart_vm(self):
        if not self.ensure_connection():
            return
        vm_name = self.get_selected_vm()
        if not vm_name:
            return
        def restart_thread():
            try:
                dom = self.conn.lookupByName(vm_name)
                if not dom.isActive():
                    self.log_to_console(f"Starting VM '{vm_name}' as it's not running")
                    dom.create()
                else:
                    dom.reboot()
                    self.log_to_console(f"VM '{vm_name}' restarting...")
                self.refresh_vm_list()
            except libvirt.libvirtError as e:
                self.log_to_console(f"Error restarting VM: {e}", error=True)
        threading.Thread(target=restart_thread).start()

    def open_console(self):
        if not self.ensure_connection():
            return
        selected = self.vm_tree.selection()
        if not selected:
            return
        vm_name = self.vm_tree.item(selected)['values'][0]
        try:
            dom = self.conn.lookupByName(vm_name)
            if not dom.isActive():
                self.log_to_console(f"VM '{vm_name}' is not running", error=True)
                return
            xml_desc = dom.XMLDesc(0)
            root = ET.fromstring(xml_desc)
            graphics = root.find('.//graphics[@type="vnc"]')
            if graphics is None:
                self.log_to_console(f"VNC graphics not configured for {vm_name}", error=True)
                return
            port = graphics.get('port')
            if port == '-1' or not port:
                time.sleep(1)
                xml_desc = dom.XMLDesc(0)
                root = ET.fromstring(xml_desc)
                graphics = root.find('.//graphics[@type="vnc"]')
                port = graphics.get('port')
            if port and port != '-1':
                subprocess.Popen(["vncviewer", f"localhost:{port}"])
                self.log_to_console(f"Opened VNC console for {vm_name} on port {port}")
            else:
                self.log_to_console(f"Unable to determine VNC port for {vm_name}", error=True)
        except libvirt.libvirtError as e:
            self.log_to_console(f"Error opening console: {e}", error=True)
        except FileNotFoundError:
            self.log_to_console("vncviewer not found. Ensure it is installed.", error=True)

    def create_vm(self):
        vm_name = self.vm_name_entry.get().strip()
        iso_path = self.iso_path_entry.get().strip()
        virtio_path = self.virtio_path_entry.get().strip()
        if not vm_name:
            messagebox.showerror("Error", "VM name is required")
            return
        if not re.match(r'^[\w-]+$', vm_name):
            messagebox.showerror("Error", "VM name can only contain letters, numbers, underscores, and hyphens")
            return
        if not os.path.exists(iso_path):
            messagebox.showerror("Error", f"Windows ISO file '{iso_path}' does not exist")
            return
        if not os.path.exists(virtio_path):
            messagebox.showerror("Error", f"VirtIO ISO file '{virtio_path}' does not exist")
            return
        try:
            memory_mb = int(self.memory_entry.get())
            vcpus = int(self.vcpu_entry.get())
            disk_gb = int(self.disk_entry.get())
            if memory_mb <= 0 or vcpus <= 0 or disk_gb <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Memory, vCPUs, and Disk size must be positive integers")
            return
        disk_dir = "/var/lib/libvirt/images"
        if not os.access(disk_dir, os.W_OK):
            messagebox.showerror("Error", f"No write permission for {disk_dir}")
            return
        try:
            network = self.network_combo.get()
            net = self.conn.networkLookupByName(network)
            if not net.isActive():
                net.create()
        except libvirt.libvirtError as e:
            available_nets = self.conn.listNetworks() + self.conn.listDefinedNetworks()
            messagebox.showerror("Network Error",
                f"Network '{network}' not available.\n"
                f"Available networks: {', '.join(available_nets) if available_nets else 'None'}")
            return
        self.create_btn.config(state=tk.DISABLED)
        self.progress_bar.start()
        def create_thread():
            safe_vm_name = slugify(vm_name)
            disk_path = f"/var/lib/libvirt/images/{safe_vm_name}.qcow2"
            try:
                cmd = ['qemu-img', 'create', '-f', 'qcow2', disk_path, f'{disk_gb}G']
                process = subprocess.run(cmd, capture_output=True, text=True)
                if process.returncode != 0:
                    self.log_to_console(f"Error creating disk: {process.stderr}", error=True)
                    return
                xml_config = f"""<domain type='kvm'>
  <name>{vm_name}</name>
  <memory unit='KiB'>{memory_mb * 1024}</memory>
  <vcpu>{vcpus}</vcpu>
  <os>
    <type arch='x86_64'>hvm</type>
    <boot dev='cdrom'/>
    <boot dev='hd'/>
  </os>
  <features>
    <acpi/>
    <apic/>
    <vmport state='off'/>
  </features>
  <cpu mode='host-passthrough'/>
  <clock offset='localtime'/>
  <devices>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='{disk_path}'/>
      <target dev='vda' bus='virtio'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>
    </disk>
    <disk type='file' device='cdrom'>
      <driver name='qemu' type='raw'/>
      <source file='{iso_path}'/>
      <target dev='sda' bus='sata'/>
      <readonly/>
      <address type='drive' controller='0' bus='0' target='0' unit='0'/>
    </disk>
    <disk type='file' device='cdrom'>
      <driver name='qemu' type='raw'/>
      <source file='{virtio_path}'/>
      <target dev='sdb' bus='sata'/>
      <readonly/>
      <address type='drive' controller='0' bus='0' target='0' unit='1'/>
    </disk>
    <controller type='sata' index='0'>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x05' function='0x0'/>
    </controller>
    <interface type='network'>
      <source network='{network}'/>
      <model type='virtio'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>
    </interface>
    <graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'/>
    <video>
      <model type='virtio'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0'/>
    </video>
    <input type='tablet' bus='usb'/>
    <input type='keyboard' bus='ps2'/>
    <input type='mouse' bus='ps2'/>
    <controller type='usb' index='0' model='ich9-ehci1'/>
    <controller type='pci' index='0' model='pci-root'/>
  </devices>
</domain>"""
                dom = self.conn.defineXML(xml_config)
                if dom:
                    self.log_to_console(f"VM '{vm_name}' defined successfully")
                    self.log_to_console(
                        "To install Windows: In the Windows installer, click 'Load driver', "
                        "select the VirtIO CDROM, and navigate to 'vioscsi\\<WindowsVersion>\\amd64' "
                        "(e.g., 'vioscsi\\w10\\amd64' for Windows 10 64-bit).")
                    try:
                        dom.create()
                        self.log_to_console(f"VM '{vm_name}' started")
                    except libvirt.libvirtError as e:
                        self.log_to_console(f"VM defined but failed to start: {e}", error=True)
                    self.root.after(0, self.clear_creation_form)
                    self.refresh_vm_list()
                else:
                    self.log_to_console("Failed to define VM", error=True)
            except libvirt.libvirtError as e:
                self.log_to_console(f"VM creation error: {e}", error=True)
                try:
                    if os.path.exists(disk_path):
                        os.unlink(disk_path)
                        self.log_to_console(f"Removed disk file: {disk_path}")
                except OSError as e:
                    self.log_to_console(f"Error removing disk file: {e}", error=True)
            finally:
                self.root.after(0, lambda: self.progress_bar.stop())
                self.root.after(0, lambda: self.create_btn.config(state=tk.NORMAL))
        threading.Thread(target=create_thread).start()

    def clear_creation_form(self):
        self.vm_name_entry.delete(0, tk.END)
        self.iso_path_entry.delete(0, tk.END)
        self.iso_path_entry.insert(0, self.iso_path)
        self.virtio_path_entry.delete(0, tk.END)
        self.virtio_path_entry.insert(0, self.virtio_path)
        self.memory_entry.delete(0, tk.END)
        self.memory_entry.insert(0, "4096")
        self.vcpu_entry.delete(0, tk.END)
        self.vcpu_entry.insert(0, "2")
        self.disk_entry.delete(0, tk.END)
        self.disk_entry.insert(0, "40")

    def delete_vm(self):
        if not self.ensure_connection():
            return
        vm_name = self.get_selected_vm()
        if not vm_name:
            return
        if not messagebox.askyesno("Confirm Delete", f"Delete VM '{vm_name}'? This cannot be undone."):
            return
        def delete_thread():
            try:
                dom = self.conn.lookupByName(vm_name)
                xml_desc = dom.XMLDesc(0)
                root = ET.fromstring(xml_desc)
                disk_path = ""
                for disk in root.findall('.//devices/disk/source'):
                    disk_path = disk.get('file')
                    if disk_path:
                        break
                if dom.isActive():
                    dom.destroy()
                dom.undefine()
                self.log_to_console(f"VM '{vm_name}' undefined")
                if disk_path and messagebox.askyesno("Delete Disk", f"Delete associated disk file at {disk_path}?"):
                    try:
                        os.unlink(disk_path)
                        self.log_to_console(f"Deleted disk: {disk_path}")
                    except OSError as e:
                        self.log_to_console(f"Error deleting disk: {e}", error=True)
                self.refresh_vm_list()
            except libvirt.libvirtError as e:
                self.log_to_console(f"Error deleting VM: {e}", error=True)
        threading.Thread(target=delete_thread).start()

    def on_closing(self):
        if self.conn:
            try:
                self.conn.close()
            except libvirt.libvirtError:
                pass
        self.root.destroy()

def main():
    root = tk.Tk()
    app = EnhancedHypervisorManagerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()