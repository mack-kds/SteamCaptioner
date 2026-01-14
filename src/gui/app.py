"""Desktop GUI for StreamCaptioner."""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
from typing import Optional, Dict

from ..config import get_config, get_settings, AppConfig, Settings
from ..audio import list_input_devices, find_device_by_name, AudioDevice


class StreamCaptionerGUI:
    """Main GUI application for StreamCaptioner."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("StreamCaptioner")
        self.root.geometry("650x500")
        self.root.minsize(500, 400)
        
        # State
        self.is_running = False
        self.selected_device: Optional[AudioDevice] = None
        self.devices: list[AudioDevice] = []
        self.config: AppConfig = get_config()
        self.settings: Settings = get_settings()
        
        # Callbacks for external control
        self.on_start = None
        self.on_stop = None
        
        # Feed status tracking
        self.feed_status: Dict[str, str] = {}
        
        self._setup_ui()
        self._refresh_devices()
        self._update_feed_list()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === Device Selection ===
        device_frame = ttk.LabelFrame(main_frame, text="Audio Device", padding="5")
        device_frame.pack(fill=tk.X, pady=(0, 10))
        
        device_row = ttk.Frame(device_frame)
        device_row.pack(fill=tk.X)
        
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(
            device_row, 
            textvariable=self.device_var,
            state="readonly",
            width=50
        )
        self.device_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.device_combo.bind("<<ComboboxSelected>>", self._on_device_selected)
        
        refresh_btn = ttk.Button(device_row, text="Refresh", command=self._refresh_devices)
        refresh_btn.pack(side=tk.RIGHT)
        
        # Device info label
        self.device_info_var = tk.StringVar(value="Select an audio device")
        device_info = ttk.Label(device_frame, textvariable=self.device_info_var, foreground="gray")
        device_info.pack(anchor=tk.W, pady=(5, 0))
        
        # === Caption Feeds ===
        feeds_frame = ttk.LabelFrame(main_frame, text="Caption Feeds", padding="5")
        feeds_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Container for treeview
        tree_container = ttk.Frame(feeds_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        # Treeview for feeds
        columns = ("name", "channel", "vmix", "status")
        self.feeds_tree = ttk.Treeview(tree_container, columns=columns, show="headings", height=4)

        self.feeds_tree.heading("name", text="Feed Name")
        self.feeds_tree.heading("channel", text="Channel")
        self.feeds_tree.heading("vmix", text="vMix Input")
        self.feeds_tree.heading("status", text="Status")

        self.feeds_tree.column("name", width=180)
        self.feeds_tree.column("channel", width=80, anchor=tk.CENTER)
        self.feeds_tree.column("vmix", width=180)
        self.feeds_tree.column("status", width=100, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.feeds_tree.yview)
        self.feeds_tree.configure(yscrollcommand=scrollbar.set)

        self.feeds_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind selection to update spinbox
        self.feeds_tree.bind("<<TreeviewSelect>>", self._on_feed_selected)

        # Channel edit controls - BELOW the treeview
        channel_edit_frame = ttk.Frame(feeds_frame)
        channel_edit_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(channel_edit_frame, text="Selected feed channel:").pack(side=tk.LEFT)
        self.channel_spinbox = ttk.Spinbox(channel_edit_frame, from_=1, to=32, width=5)
        self.channel_spinbox.set(1)
        self.channel_spinbox.pack(side=tk.LEFT, padx=5)
        self.apply_channel_btn = ttk.Button(channel_edit_frame, text="Set Channel", command=self._apply_channel)
        self.apply_channel_btn.pack(side=tk.LEFT, padx=5)

        # Show which feed is selected
        self.selected_feed_var = tk.StringVar(value="(select a feed above)")
        ttk.Label(channel_edit_frame, textvariable=self.selected_feed_var, foreground="gray").pack(side=tk.LEFT, padx=10)
        
        # === Web Server Info ===
        web_frame = ttk.LabelFrame(main_frame, text="Web Server", padding="5")
        web_frame.pack(fill=tk.X, pady=(0, 10))
        
        web_row = ttk.Frame(web_frame)
        web_row.pack(fill=tk.X)
        
        self.web_url_var = tk.StringVar(value=f"http://localhost:{self.config.web.port}")
        url_label = ttk.Label(web_row, textvariable=self.web_url_var, foreground="blue", cursor="hand2")
        url_label.pack(side=tk.LEFT)
        url_label.bind("<Button-1>", self._open_web_ui)
        
        self.web_status_var = tk.StringVar(value="Not running")
        web_status = ttk.Label(web_row, textvariable=self.web_status_var, foreground="gray")
        web_status.pack(side=tk.RIGHT)
        
        # === Controls ===
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_btn = ttk.Button(
            control_frame, 
            text="Start Captioning",
            command=self._toggle_captioning,
            style="Accent.TButton"
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # === Status Bar ===
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_var = tk.StringVar(value="Ready - Select an audio device to begin")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X)
    
    def _refresh_devices(self):
        """Refresh the list of audio devices."""
        try:
            self.devices = list_input_devices()
            device_names = [f"{d.name} ({d.channels}ch)" for d in self.devices]
            self.device_combo["values"] = device_names
            
            # Try to select Focusrite by default
            focusrite = find_device_by_name("Focusrite")
            if focusrite:
                for i, d in enumerate(self.devices):
                    if d.id == focusrite.id:
                        self.device_combo.current(i)
                        self._on_device_selected(None)
                        break
            elif self.devices:
                self.device_combo.current(0)
                self._on_device_selected(None)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list audio devices: {e}")
    
    def _on_device_selected(self, event):
        """Handle device selection."""
        idx = self.device_combo.current()
        if 0 <= idx < len(self.devices):
            self.selected_device = self.devices[idx]
            self.device_info_var.set(
                f"Device ID: {self.selected_device.id}, "
                f"Channels: {self.selected_device.channels}, "
                f"Sample Rate: {self.selected_device.default_sample_rate}Hz"
            )
            self.status_var.set(f"Selected: {self.selected_device.name}")

    def _update_feed_list(self):
        """Update the feed list display."""
        # Clear existing items
        for item in self.feeds_tree.get_children():
            self.feeds_tree.delete(item)

        # Add feeds from config
        for feed in self.config.feeds:
            status = self.feed_status.get(feed.id, "Ready")
            self.feeds_tree.insert("", tk.END, iid=feed.id, values=(
                feed.name,
                f"Ch {feed.channel + 1}",  # Display as 1-based
                feed.vmix_input or "-",
                status
            ))

    def _on_feed_selected(self, event):
        """Handle feed selection - update spinbox with current channel."""
        item = self.feeds_tree.selection()
        if item:
            feed_id = item[0]
            # Find the feed and set spinbox to current channel
            for feed in self.config.feeds:
                if feed.id == feed_id:
                    self.channel_spinbox.set(feed.channel + 1)  # 1-based display
                    self.selected_feed_var.set(f"→ {feed.name}")
                    break

    def _apply_channel(self):
        """Apply channel change to selected feed."""
        item = self.feeds_tree.selection()
        if not item:
            messagebox.showinfo("Info", "Select a feed first")
            return

        feed_id = item[0]
        try:
            new_channel = int(self.channel_spinbox.get()) - 1  # Convert to 0-based
            if new_channel < 0:
                new_channel = 0
        except ValueError:
            messagebox.showerror("Error", "Invalid channel number")
            return

        # Update the feed config
        for feed in self.config.feeds:
            if feed.id == feed_id:
                feed.channel = new_channel
                self.status_var.set(f"Set {feed.name} to Channel {new_channel + 1}")
                break

        self._update_feed_list()

    def _toggle_captioning(self):
        """Toggle captioning on/off."""
        if self.is_running:
            self._stop_captioning()
        else:
            self._start_captioning()

    def _start_captioning(self):
        """Start the captioning system."""
        if not self.selected_device:
            messagebox.showwarning("Warning", "Please select an audio device first.")
            return

        if not self.settings.deepgram_api_key:
            messagebox.showerror("Error", "Deepgram API key not configured. Check your .env file.")
            return

        self.is_running = True
        self.start_btn.config(text="Stop Captioning")
        self.device_combo.config(state="disabled")
        self.status_var.set("Starting captioning...")
        self.web_status_var.set("Running")

        # Update feed statuses
        for feed in self.config.feeds:
            self.feed_status[feed.id] = "Starting..."
        self._update_feed_list()

        # Call external start handler
        if self.on_start:
            threading.Thread(target=self.on_start, args=(self.selected_device,), daemon=True).start()

        self.status_var.set("Captioning active")

    def _stop_captioning(self):
        """Stop the captioning system."""
        self.is_running = False
        self.start_btn.config(text="Start Captioning")
        self.device_combo.config(state="readonly")
        self.status_var.set("Stopped")
        self.web_status_var.set("Not running")

        # Update feed statuses
        for feed in self.config.feeds:
            self.feed_status[feed.id] = "Stopped"
        self._update_feed_list()

        # Call external stop handler
        if self.on_stop:
            self.on_stop()

    def _open_web_ui(self, event=None):
        """Open the web UI in browser."""
        url = self.web_url_var.get()
        webbrowser.open(url)

    def update_feed_status(self, feed_id: str, status: str):
        """Update the status of a feed (thread-safe)."""
        self.feed_status[feed_id] = status
        self.root.after(0, self._update_feed_list)

    def update_status(self, message: str):
        """Update the status bar (thread-safe)."""
        self.root.after(0, lambda: self.status_var.set(message))

    def set_web_url(self, url: str):
        """Set the web server URL."""
        self.web_url_var.set(url)

    def run(self):
        """Run the GUI main loop."""
        self.root.mainloop()

    def quit(self):
        """Quit the application."""
        if self.is_running:
            self._stop_captioning()
        self.root.quit()


if __name__ == "__main__":
    # Test the GUI
    app = StreamCaptionerGUI()
    app.run()

