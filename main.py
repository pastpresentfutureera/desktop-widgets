"""
Desktop Widgets Application
- Calendar, To-Do List, Day Planner, Weekly Planner, Monthly Planner, Pomodoro Timer
- Widgets stick to desktop and persist after restart
"""

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, simpledialog
import json
import os
from datetime import datetime, timedelta
import calendar
import threading
import time
import sys

# Windows-specific imports for desktop integration
try:
    import ctypes
    from ctypes import wintypes
    import winreg
    WINDOWS = True
except ImportError:
    WINDOWS = False

# ============== CONFIGURATION ==============
DATA_FILE = os.path.join(os.path.expanduser("~"), "desktop_widgets_data.json")
CONFIG_FILE = os.path.join(os.path.expanduser("~"), "desktop_widgets_config.json")

# Default light colors for widgets
DEFAULT_COLORS = {
    "calendar": "#FFE4E1",      # Misty Rose
    "todo": "#E0FFE0",          # Light Green
    "day_planner": "#E6E6FA",   # Lavender
    "weekly_planner": "#FFEFD5", # Papaya Whip
    "monthly_planner": "#E0FFFF", # Light Cyan
    "pomodoro": "#FFF0F5"       # Lavender Blush
}

# ============== DATA MANAGEMENT ==============
class DataManager:
    def __init__(self):
        self.data = self.load_data()
        self.config = self.load_config()
    
    def load_data(self):
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {
            "calendar_events": {},
            "todos": [],
            "day_plans": {},
            "weekly_plans": {},
            "monthly_plans": {},
            "pomodoro_history": {},
            "pomodoro_settings": {"focus": 25, "break": 5}
        }
    
    def save_data(self):
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {
            "colors": DEFAULT_COLORS.copy(),
            "positions": {},
            "sizes": {},
            "expanded": {}
        }
    
    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

data_manager = DataManager()

# ============== DESKTOP INTEGRATION (Windows) ==============
def get_window_handle(window):
    """Get the Windows handle for a tkinter window"""
    if not WINDOWS:
        return None
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        return hwnd
    except:
        return None

def make_desktop_widget(window):
    """Make window stick to desktop on Windows"""
    if not WINDOWS:
        return
    
    try:
        hwnd = get_window_handle(window)
        if not hwnd:
            return
        
        # Set extended window style to tool window (no taskbar icon)
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_NOACTIVATE = 0x08000000
        
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        
        # Find the desktop window (Program Manager)
        progman = ctypes.windll.user32.FindWindowW("Progman", None)
        
        # Send window to bottom (above desktop icons, below other windows)
        HWND_BOTTOM = 1
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_NOACTIVATE = 0x0010
        
        ctypes.windll.user32.SetWindowPos(
            hwnd, HWND_BOTTOM, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
        )
    except Exception as e:
        print(f"Desktop integration error: {e}")

def send_to_desktop_level(window):
    """Continuously keep window at desktop level"""
    if not WINDOWS:
        return
    
    def keep_at_bottom():
        while True:
            try:
                if not window.winfo_exists():
                    break
                hwnd = get_window_handle(window)
                if hwnd:
                    HWND_BOTTOM = 1
                    SWP_NOSIZE = 0x0001
                    SWP_NOMOVE = 0x0002
                    SWP_NOACTIVATE = 0x0010
                    
                    ctypes.windll.user32.SetWindowPos(
                        hwnd, HWND_BOTTOM, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                    )
            except:
                break
            time.sleep(1)
    
    thread = threading.Thread(target=keep_at_bottom, daemon=True)
    thread.start()

def add_to_startup():
    """Add application to Windows startup"""
    if not WINDOWS:
        return False
    
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        
        # Get the path to this executable or script
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            app_path = sys.executable
        else:
            # Running as script
            app_path = os.path.abspath(sys.argv[0])
            python_path = sys.executable
            app_path = f'"{python_path}" "{app_path}"'
        
        winreg.SetValueEx(key, "DesktopWidgets", 0, winreg.REG_SZ, app_path)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Startup registration error: {e}")
        return False

def remove_from_startup():
    """Remove application from Windows startup"""
    if not WINDOWS:
        return False
    
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, "DesktopWidgets")
        winreg.CloseKey(key)
        return True
    except:
        return False

def is_in_startup():
    """Check if application is in startup"""
    if not WINDOWS:
        return False
    
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        winreg.QueryValueEx(key, "DesktopWidgets")
        winreg.CloseKey(key)
        return True
    except:
        return False

# ============== BASE WIDGET CLASS ==============
class BaseWidget(tk.Toplevel):
    def __init__(self, master, widget_name, title, min_width=250, min_height=200):
        super().__init__(master)
        
        self.widget_name = widget_name
        self.min_width = min_width
        self.min_height = min_height
        self.expanded = data_manager.config.get("expanded", {}).get(widget_name, False)
        self.master_ref = master
        
        # Window setup
        self.title(title)
        self.overrideredirect(True)  # Remove window decorations
        self.attributes('-topmost', False)
        
        # Set color
        self.bg_color = data_manager.config.get("colors", DEFAULT_COLORS).get(
            widget_name, DEFAULT_COLORS.get(widget_name, "#FFFFFF")
        )
        self.configure(bg=self.bg_color)
        
        # Load position and size
        pos = data_manager.config.get("positions", {}).get(widget_name, None)
        size = data_manager.config.get("sizes", {}).get(widget_name, None)
        
        if size:
            w, h = size
        else:
            w, h = min_width, min_height
        
        if pos:
            x, y = pos
        else:
            x, y = 100, 100
        
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(min_width, min_height)
        
        # Create main container with border
        self.main_frame = tk.Frame(self, bg=self.bg_color, 
                                   highlightbackground="#888888", 
                                   highlightthickness=2)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title bar
        self.create_title_bar(title)
        
        # Content area
        self.content_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Resize grip
        self.create_resize_grip()
        
        # Make widget stick to desktop after window is ready
        self.after(500, lambda: make_desktop_widget(self))
        self.after(1000, lambda: send_to_desktop_level(self))
        
        # Save position on move
        self.bind("<Configure>", self.on_configure)
    
    def create_title_bar(self, title):
        title_bar = tk.Frame(self.main_frame, bg=self.darken_color(self.bg_color, 0.85))
        title_bar.pack(fill=tk.X)
        
        # Drag functionality
        title_bar.bind("<Button-1>", self.start_drag)
        title_bar.bind("<B1-Motion>", self.on_drag)
        
        # Title label
        title_label = tk.Label(
            title_bar, text=title, bg=self.darken_color(self.bg_color, 0.85),
            font=("Segoe UI", 10, "bold"), fg="#333333"
        )
        title_label.pack(side=tk.LEFT, padx=8, pady=5)
        title_label.bind("<Button-1>", self.start_drag)
        title_label.bind("<B1-Motion>", self.on_drag)
        
        # Buttons frame
        btn_frame = tk.Frame(title_bar, bg=self.darken_color(self.bg_color, 0.85))
        btn_frame.pack(side=tk.RIGHT, padx=3)
        
        # Color button
        color_btn = tk.Button(
            btn_frame, text="🎨", font=("Segoe UI", 9), relief=tk.FLAT,
            bg=self.darken_color(self.bg_color, 0.85), command=self.change_color,
            width=2, cursor="hand2", bd=0
        )
        color_btn.pack(side=tk.LEFT, padx=2)
        
        # Expand/Collapse button
        self.expand_btn = tk.Button(
            btn_frame, text="⬇" if not self.expanded else "⬆", font=("Segoe UI", 9),
            relief=tk.FLAT, bg=self.darken_color(self.bg_color, 0.85),
            command=self.toggle_expand, width=2, cursor="hand2", bd=0
        )
        self.expand_btn.pack(side=tk.LEFT, padx=2)
        
        # Close button
        close_btn = tk.Button(
            btn_frame, text="✕", font=("Segoe UI", 9), relief=tk.FLAT,
            bg=self.darken_color(self.bg_color, 0.85), fg="#CC0000",
            command=self.hide_widget, width=2, cursor="hand2", bd=0
        )
        close_btn.pack(side=tk.LEFT, padx=2)
    
    def create_resize_grip(self):
        grip = tk.Label(self.main_frame, text="⋱", bg=self.bg_color, 
                       fg="#888888", cursor="bottom_right_corner", font=("Arial", 10))
        grip.place(relx=1.0, rely=1.0, anchor="se")
        grip.bind("<Button-1>", self.start_resize)
        grip.bind("<B1-Motion>", self.on_resize)
    
    def start_drag(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def on_drag(self, event):
        x = self.winfo_x() + event.x - self.drag_start_x
        y = self.winfo_y() + event.y - self.drag_start_y
        self.geometry(f"+{x}+{y}")
    
    def start_resize(self, event):
        self.resize_start_x = event.x_root
        self.resize_start_y = event.y_root
        self.resize_start_w = self.winfo_width()
        self.resize_start_h = self.winfo_height()
    
    def on_resize(self, event):
        dx = event.x_root - self.resize_start_x
        dy = event.y_root - self.resize_start_y
        new_w = max(self.min_width, self.resize_start_w + dx)
        new_h = max(self.min_height, self.resize_start_h + dy)
        self.geometry(f"{new_w}x{new_h}")
    
    def on_configure(self, event):
        # Save position and size
        if event.widget == self:
            self.save_position()
            self.save_size()
    
    def save_position(self):
        if "positions" not in data_manager.config:
            data_manager.config["positions"] = {}
        data_manager.config["positions"][self.widget_name] = [self.winfo_x(), self.winfo_y()]
        data_manager.save_config()
    
    def save_size(self):
        if "sizes" not in data_manager.config:
            data_manager.config["sizes"] = {}
        data_manager.config["sizes"][self.widget_name] = [self.winfo_width(), self.winfo_height()]
        data_manager.save_config()
    
    def change_color(self):
        color = colorchooser.askcolor(
            title=f"Choose color for {self.widget_name}",
            initialcolor=self.bg_color
        )[1]
        if color:
            self.bg_color = color
            if "colors" not in data_manager.config:
                data_manager.config["colors"] = {}
            data_manager.config["colors"][self.widget_name] = color
            data_manager.save_config()
            self.apply_color(color)
    
    def apply_color(self, color):
        self.configure(bg=color)
        self.main_frame.configure(bg=color)
        self.content_frame.configure(bg=color)
        self.update_widget_colors(self.main_frame, color)
    
    def update_widget_colors(self, parent, color):
        for widget in parent.winfo_children():
            try:
                if isinstance(widget, (tk.Frame, tk.Label)):
                    widget.configure(bg=color)
                self.update_widget_colors(widget, color)
            except:
                pass
    
    def toggle_expand(self):
        self.expanded = not self.expanded
        if "expanded" not in data_manager.config:
            data_manager.config["expanded"] = {}
        data_manager.config["expanded"][self.widget_name] = self.expanded
        data_manager.save_config()
        
        self.expand_btn.config(text="⬆" if self.expanded else "⬇")
        
        # Adjust size
        if self.expanded:
            current_h = self.winfo_height()
            new_h = min(current_h + 150, 600)
            self.geometry(f"{self.winfo_width()}x{new_h}")
        
        self.update_content()
    
    def update_content(self):
        """Override in subclasses"""
        pass
    
    def hide_widget(self):
        self.withdraw()
    
    def show_widget(self):
        self.deiconify()
        self.after(100, lambda: make_desktop_widget(self))
    
    def darken_color(self, hex_color, factor=0.9):
        """Darken a hex color"""
        try:
            hex_color = hex_color.lstrip('#')
            r = int(int(hex_color[0:2], 16) * factor)
            g = int(int(hex_color[2:4], 16) * factor)
            b = int(int(hex_color[4:6], 16) * factor)
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color

# ============== CALENDAR WIDGET ==============
class CalendarWidget(BaseWidget):
    def __init__(self, master):
        super().__init__(master, "calendar", "📅 Calendar", 300, 350)
        self.current_date = datetime.now()
        self.selected_date = datetime.now().strftime("%Y-%m-%d")
        self.create_content()
    
    def create_content(self):
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Navigation
        nav_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        nav_frame.pack(fill=tk.X, pady=(0, 8))
        
        prev_btn = tk.Button(nav_frame, text="◀", command=self.prev_month,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2",
                            font=("Segoe UI", 11))
        prev_btn.pack(side=tk.LEFT)
        
        self.month_label = tk.Label(
            nav_frame, text=self.current_date.strftime("%B %Y"),
            bg=self.bg_color, font=("Segoe UI", 12, "bold")
        )
        self.month_label.pack(side=tk.LEFT, expand=True)
        
        next_btn = tk.Button(nav_frame, text="▶", command=self.next_month,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2",
                            font=("Segoe UI", 11))
        next_btn.pack(side=tk.RIGHT)
        
        # Days header
        days_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        days_frame.pack(fill=tk.X)
        days_frame.columnconfigure(tuple(range(7)), weight=1, uniform="day")
        
        days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for i, day in enumerate(days):
            lbl = tk.Label(days_frame, text=day, bg=self.darken_color(self.bg_color, 0.9), 
                          font=("Segoe UI", 9, "bold"), relief=tk.RIDGE)
            lbl.grid(row=0, column=i, sticky="nsew", padx=1, pady=1)
        
        # Calendar grid
        self.cal_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        self.cal_frame.pack(fill=tk.BOTH, expand=True)
        
        for i in range(7):
            self.cal_frame.columnconfigure(i, weight=1, uniform="day")
        
        self.update_calendar()
        
        # Event section (always show in compact, more features when expanded)
        self.create_event_section()
    
    def create_event_section(self):
        event_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        event_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        
        # Selected date label
        self.selected_label = tk.Label(
            event_frame, text=f"📌 {self.selected_date}", 
            bg=self.bg_color, font=("Segoe UI", 9, "bold")
        )
        self.selected_label.pack(anchor="w")
        
        # Event list
        list_frame = tk.Frame(event_frame, bg=self.bg_color)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        height = 5 if self.expanded else 3
        self.event_listbox = tk.Listbox(list_frame, height=height, font=("Segoe UI", 9),
                                        yscrollcommand=scrollbar.set)
        self.event_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.event_listbox.yview)
        
        # Buttons
        btn_frame = tk.Frame(event_frame, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        add_btn = tk.Button(btn_frame, text="+ Add", command=self.add_event,
                           bg="#90EE90", cursor="hand2", font=("Segoe UI", 9))
        add_btn.pack(side=tk.LEFT, padx=2)
        
        del_btn = tk.Button(btn_frame, text="- Delete", command=self.delete_event,
                           bg="#FFB6C1", cursor="hand2", font=("Segoe UI", 9))
        del_btn.pack(side=tk.LEFT, padx=2)
        
        if self.expanded:
            clear_btn = tk.Button(btn_frame, text="Clear All", command=self.clear_events,
                                 bg="#FF6B6B", cursor="hand2", font=("Segoe UI", 9))
            clear_btn.pack(side=tk.LEFT, padx=2)
        
        self.load_events()
    
    def update_calendar(self):
        for widget in self.cal_frame.winfo_children():
            widget.destroy()
        
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(
            self.current_date.year, self.current_date.month
        )
        
        today = datetime.now()
        
        for row_idx, week in enumerate(month_days):
            self.cal_frame.rowconfigure(row_idx, weight=1)
            
            for col_idx, day in enumerate(week):
                if day == 0:
                    lbl = tk.Label(self.cal_frame, text="", bg="#EEEEEE")
                else:
                    date_key = f"{self.current_date.year}-{self.current_date.month:02d}-{day:02d}"
                    has_event = date_key in data_manager.data.get("calendar_events", {})
                    is_selected = date_key == self.selected_date
                    
                    # Determine background color
                    if day == today.day and self.current_date.month == today.month and self.current_date.year == today.year:
                        bg = "#FFD700"  # Gold for today
                    elif is_selected:
                        bg = "#87CEEB"  # Light blue for selected
                    elif has_event:
                        bg = "#98FB98"  # Pale green for events
                    else:
                        bg = "white"
                    
                    # Create cell frame for day + event indicator
                    cell = tk.Frame(self.cal_frame, bg=bg, relief=tk.RIDGE, bd=1)
                    
                    day_lbl = tk.Label(cell, text=str(day), bg=bg, 
                                      font=("Segoe UI", 10), cursor="hand2")
                    day_lbl.pack()
                    
                    if has_event:
                        event_count = len(data_manager.data["calendar_events"][date_key])
                        dot_lbl = tk.Label(cell, text=f"•{event_count}", bg=bg, 
                                          fg="#FF4500", font=("Segoe UI", 7))
                        dot_lbl.pack()
                        dot_lbl.bind("<Button-1>", lambda e, d=day: self.select_date(d))
                    
                    day_lbl.bind("<Button-1>", lambda e, d=day: self.select_date(d))
                    cell.bind("<Button-1>", lambda e, d=day: self.select_date(d))
                    
                    lbl = cell
                
                lbl.grid(row=row_idx, column=col_idx, sticky="nsew", padx=1, pady=1)
        
        self.month_label.config(text=self.current_date.strftime("%B %Y"))
    
    def select_date(self, day):
        self.selected_date = f"{self.current_date.year}-{self.current_date.month:02d}-{day:02d}"
        self.selected_label.config(text=f"📌 {self.selected_date}")
        self.update_calendar()
        self.load_events()
    
    def prev_month(self):
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year-1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month-1)
        self.update_calendar()
    
    def next_month(self):
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year+1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month+1)
        self.update_calendar()
    
    def add_event(self):
        event = simpledialog.askstring("Add Event", f"Event for {self.selected_date}:",
                                       parent=self)
        if event:
            if "calendar_events" not in data_manager.data:
                data_manager.data["calendar_events"] = {}
            if self.selected_date not in data_manager.data["calendar_events"]:
                data_manager.data["calendar_events"][self.selected_date] = []
            data_manager.data["calendar_events"][self.selected_date].append(event)
            data_manager.save_data()
            self.load_events()
            self.update_calendar()
    
    def delete_event(self):
        selection = self.event_listbox.curselection()
        if selection:
            idx = selection[0]
            events = data_manager.data.get("calendar_events", {}).get(self.selected_date, [])
            if idx < len(events):
                events.pop(idx)
                if not events:
                    del data_manager.data["calendar_events"][self.selected_date]
                data_manager.save_data()
                self.load_events()
                self.update_calendar()
    
    def clear_events(self):
        if self.selected_date in data_manager.data.get("calendar_events", {}):
            if messagebox.askyesno("Confirm", f"Clear all events for {self.selected_date}?"):
                del data_manager.data["calendar_events"][self.selected_date]
                data_manager.save_data()
                self.load_events()
                self.update_calendar()
    
    def load_events(self):
        self.event_listbox.delete(0, tk.END)
        events = data_manager.data.get("calendar_events", {}).get(self.selected_date, [])
        for event in events:
            self.event_listbox.insert(tk.END, f"• {event}")
    
    def update_content(self):
        self.create_content()

# ============== TODO LIST WIDGET ==============
class TodoWidget(BaseWidget):
    def __init__(self, master):
        super().__init__(master, "todo", "✅ To-Do List", 280, 280)
        self.create_content()
    
    def create_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Input frame
        input_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        input_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.todo_entry = tk.Entry(input_frame, font=("Segoe UI", 10))
        self.todo_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.todo_entry.bind("<Return>", lambda e: self.add_todo())
        
        add_btn = tk.Button(input_frame, text="+", command=self.add_todo,
                           bg="#90EE90", width=3, cursor="hand2", font=("Segoe UI", 10, "bold"))
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Stats (when expanded)
        if self.expanded:
            todos = data_manager.data.get("todos", [])
            done = len([t for t in todos if t["done"]])
            total = len(todos)
            stats_lbl = tk.Label(self.content_frame, 
                                text=f"Progress: {done}/{total} completed",
                                bg=self.bg_color, font=("Segoe UI", 9))
            stats_lbl.pack(anchor="w")
        
        # Todo list with scrollbar
        list_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.todo_canvas = tk.Canvas(list_frame, bg=self.bg_color, 
                                     yscrollcommand=scrollbar.set, highlightthickness=0)
        self.todo_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.todo_canvas.yview)
        
        self.todo_inner_frame = tk.Frame(self.todo_canvas, bg=self.bg_color)
        self.todo_canvas.create_window((0, 0), window=self.todo_inner_frame, anchor="nw")
        
        self.todo_inner_frame.bind("<Configure>", 
            lambda e: self.todo_canvas.configure(scrollregion=self.todo_canvas.bbox("all")))
        
        self.load_todos()
        
        # Options (when expanded)
        if self.expanded:
            opt_frame = tk.Frame(self.content_frame, bg=self.bg_color)
            opt_frame.pack(fill=tk.X, pady=(8, 0))
            
            clear_done_btn = tk.Button(opt_frame, text="Clear Done", 
                                       command=self.clear_completed,
                                       bg="#FFB6C1", cursor="hand2", font=("Segoe UI", 9))
            clear_done_btn.pack(side=tk.LEFT)
            
            clear_all_btn = tk.Button(opt_frame, text="Clear All", 
                                      command=self.clear_all,
                                      bg="#FF6B6B", cursor="hand2", font=("Segoe UI", 9))
            clear_all_btn.pack(side=tk.LEFT, padx=(5, 0))
    
    def add_todo(self):
        text = self.todo_entry.get().strip()
        if text:
            if "todos" not in data_manager.data:
                data_manager.data["todos"] = []
            data_manager.data["todos"].append({"text": text, "done": False})
            data_manager.save_data()
            self.todo_entry.delete(0, tk.END)
            self.load_todos()
            if self.expanded:
                self.create_content()  # Refresh stats
    
    def load_todos(self):
        for widget in self.todo_inner_frame.winfo_children():
            widget.destroy()
        
        todos = data_manager.data.get("todos", [])
        for i, todo in enumerate(todos):
            todo_frame = tk.Frame(self.todo_inner_frame, bg=self.bg_color)
            todo_frame.pack(fill=tk.X, pady=2)
            
            var = tk.BooleanVar(value=todo["done"])
            cb = tk.Checkbutton(
                todo_frame, variable=var, bg=self.bg_color,
                command=lambda idx=i, v=var: self.toggle_todo(idx, v),
                activebackground=self.bg_color
            )
            cb.pack(side=tk.LEFT)
            
            text = todo["text"]
            fg = "#888888" if todo["done"] else "#000000"
            font_style = ("Segoe UI", 10, "overstrike") if todo["done"] else ("Segoe UI", 10)
            
            lbl = tk.Label(todo_frame, text=text, bg=self.bg_color, fg=fg, 
                          font=font_style, anchor="w", wraplength=180)
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            del_btn = tk.Button(todo_frame, text="✕", command=lambda idx=i: self.delete_todo(idx),
                               bg=self.bg_color, fg="#CC0000", relief=tk.FLAT,
                               cursor="hand2", font=("Segoe UI", 9))
            del_btn.pack(side=tk.RIGHT)
    
    def toggle_todo(self, idx, var):
        data_manager.data["todos"][idx]["done"] = var.get()
        data_manager.save_data()
        self.load_todos()
        if self.expanded:
            self.create_content()
    
    def delete_todo(self, idx):
        data_manager.data["todos"].pop(idx)
        data_manager.save_data()
        self.load_todos()
        if self.expanded:
            self.create_content()
    
    def clear_completed(self):
        data_manager.data["todos"] = [t for t in data_manager.data.get("todos", []) if not t["done"]]
        data_manager.save_data()
        self.load_todos()
        self.create_content()
    
    def clear_all(self):
        if messagebox.askyesno("Confirm", "Clear all todos?"):
            data_manager.data["todos"] = []
            data_manager.save_data()
            self.load_todos()
            self.create_content()
    
    def update_content(self):
        self.create_content()

# ============== DAY PLANNER WIDGET ==============
class DayPlannerWidget(BaseWidget):
    def __init__(self, master):
        super().__init__(master, "day_planner", "📋 Day Planner", 300, 380)
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.create_content()
    
    def create_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Date navigation
        nav_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        nav_frame.pack(fill=tk.X, pady=(0, 8))
        
        prev_btn = tk.Button(nav_frame, text="◀", command=self.prev_day,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2",
                            font=("Segoe UI", 11))
        prev_btn.pack(side=tk.LEFT)
        
        # Format date nicely
        date_obj = datetime.strptime(self.current_date, "%Y-%m-%d")
        date_display = date_obj.strftime("%A, %b %d")
        
        self.date_label = tk.Label(nav_frame, text=date_display,
                                   bg=self.bg_color, font=("Segoe UI", 11, "bold"))
        self.date_label.pack(side=tk.LEFT, expand=True)
        
        next_btn = tk.Button(nav_frame, text="▶", command=self.next_day,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2",
                            font=("Segoe UI", 11))
        next_btn.pack(side=tk.RIGHT)
        
        today_btn = tk.Button(nav_frame, text="Today", command=self.goto_today,
                             bg="#90EE90", cursor="hand2", font=("Segoe UI", 9))
        today_btn.pack(side=tk.RIGHT, padx=5)
        
        # Time slots with scrollbar
        slots_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        slots_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(slots_frame, bg=self.bg_color, highlightthickness=0)
        scrollbar = tk.Scrollbar(slots_frame, orient="vertical", command=canvas.yview)
        self.slots_inner = tk.Frame(canvas, bg=self.bg_color)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0, 0), window=self.slots_inner, anchor="nw")
        
        self.slots_inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Create time slots
        hours = range(5, 24) if self.expanded else range(7, 20)
        for hour in hours:
            self.create_time_slot(hour)
    
    def create_time_slot(self, hour):
        slot_frame = tk.Frame(self.slots_inner, bg=self.bg_color)
        slot_frame.pack(fill=tk.X, pady=1)
        
        # Time label with AM/PM
        if hour < 12:
            time_str = f"{hour:2d}:00 AM"
        elif hour == 12:
            time_str = "12:00 PM"
        else:
            time_str = f"{hour-12:2d}:00 PM"
        
        time_label = tk.Label(slot_frame, text=time_str, 
                             bg=self.darken_color(self.bg_color, 0.9), 
                             font=("Segoe UI", 9), width=8, relief=tk.RIDGE)
        time_label.pack(side=tk.LEFT)
        
        key = f"{self.current_date}_{hour}"
        current_text = data_manager.data.get("day_plans", {}).get(key, "")
        
        entry = tk.Entry(slot_frame, font=("Segoe UI", 9))
        entry.insert(0, current_text)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        entry.bind("<FocusOut>", lambda e, k=key, en=entry: self.save_slot(k, en))
        entry.bind("<Return>", lambda e, k=key, en=entry: self.save_slot(k, en))
        
        # Color coding for filled slots
        if current_text:
            entry.configure(bg="#FFFACD")
    
    def save_slot(self, key, entry):
        if "day_plans" not in data_manager.data:
            data_manager.data["day_plans"] = {}
        text = entry.get().strip()
        if text:
            data_manager.data["day_plans"][key] = text
            entry.configure(bg="#FFFACD")
        else:
            if key in data_manager.data["day_plans"]:
                del data_manager.data["day_plans"][key]
            entry.configure(bg="white")
        data_manager.save_data()
    
    def prev_day(self):
        date = datetime.strptime(self.current_date, "%Y-%m-%d")
        self.current_date = (date - timedelta(days=1)).strftime("%Y-%m-%d")
        self.create_content()
    
    def next_day(self):
        date = datetime.strptime(self.current_date, "%Y-%m-%d")
        self.current_date = (date + timedelta(days=1)).strftime("%Y-%m-%d")
        self.create_content()
    
    def goto_today(self):
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.create_content()
    
    def update_content(self):
        self.create_content()

# ============== WEEKLY PLANNER WIDGET ==============
class WeeklyPlannerWidget(BaseWidget):
    def __init__(self, master):
        super().__init__(master, "weekly_planner", "📆 Weekly Planner", 600, 380)
        self.current_week_start = self.get_week_start(datetime.now())
        self.create_content()
    
    def get_week_start(self, date):
        return date - timedelta(days=date.weekday())
    
    def create_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Navigation
        nav_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        nav_frame.pack(fill=tk.X, pady=(0, 8))
        
        prev_btn = tk.Button(nav_frame, text="◀ Prev Week", command=self.prev_week,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2",
                            font=("Segoe UI", 9))
        prev_btn.pack(side=tk.LEFT)
        
        week_end = self.current_week_start + timedelta(days=6)
        week_text = f"{self.current_week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"
        self.week_label = tk.Label(nav_frame, text=week_text,
                                   bg=self.bg_color, font=("Segoe UI", 11, "bold"))
        self.week_label.pack(side=tk.LEFT, expand=True)
        
        next_btn = tk.Button(nav_frame, text="Next Week ▶", command=self.next_week,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2",
                            font=("Segoe UI", 9))
        next_btn.pack(side=tk.RIGHT)
        
        this_week_btn = tk.Button(nav_frame, text="This Week", command=self.goto_this_week,
                                  bg="#90EE90", cursor="hand2", font=("Segoe UI", 9))
        this_week_btn.pack(side=tk.RIGHT, padx=5)
        
        # Days grid
        grid_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        grid_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid columns to be equal
        for i in range(7):
            grid_frame.columnconfigure(i, weight=1, uniform="day")
        grid_frame.rowconfigure(1, weight=1)
        
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        today = datetime.now().date()
        
        for i, day_name in enumerate(days):
            day_date = self.current_week_start + timedelta(days=i)
            date_str = day_date.strftime("%Y-%m-%d")
            is_today = day_date.date() == today
            
            # Header with weekday name
            header_bg = "#FFD700" if is_today else self.darken_color(self.bg_color, 0.85)
            header = tk.Frame(grid_frame, bg=header_bg, relief=tk.RIDGE, bd=1)
            header.grid(row=0, column=i, sticky="nsew", padx=1, pady=1)
            
            day_name_lbl = tk.Label(header, text=day_name[:3].upper(), bg=header_bg, 
                                   font=("Segoe UI", 9, "bold"))
            day_name_lbl.pack()
            
            day_num_lbl = tk.Label(header, text=str(day_date.day), bg=header_bg,
                                  font=("Segoe UI", 11, "bold"))
            day_num_lbl.pack()
            
            # Content area
            day_frame = tk.Frame(grid_frame, bg="white", relief=tk.SUNKEN, bd=1)
            day_frame.grid(row=1, column=i, sticky="nsew", padx=1, pady=1)
            
            # Text widget for plans
            height = 12 if self.expanded else 8
            text = tk.Text(day_frame, font=("Segoe UI", 8), wrap=tk.WORD, 
                          height=height, width=10, relief=tk.FLAT)
            text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            
            # Load existing content
            content = data_manager.data.get("weekly_plans", {}).get(date_str, "")
            text.insert("1.0", content)
            text.bind("<FocusOut>", lambda e, d=date_str, t=text: self.save_day(d, t))
    
    def save_day(self, date_str, text_widget):
        if "weekly_plans" not in data_manager.data:
            data_manager.data["weekly_plans"] = {}
        content = text_widget.get("1.0", tk.END).strip()
        if content:
            data_manager.data["weekly_plans"][date_str] = content
        elif date_str in data_manager.data["weekly_plans"]:
            del data_manager.data["weekly_plans"][date_str]
        data_manager.save_data()
    
    def prev_week(self):
        self.current_week_start -= timedelta(days=7)
        self.create_content()
    
    def next_week(self):
        self.current_week_start += timedelta(days=7)
        self.create_content()
    
    def goto_this_week(self):
        self.current_week_start = self.get_week_start(datetime.now())
        self.create_content()
    
    def update_content(self):
        self.create_content()

# ============== MONTHLY PLANNER WIDGET ==============
class MonthlyPlannerWidget(BaseWidget):
    def __init__(self, master):
        super().__init__(master, "monthly_planner", "🗓️ Monthly Planner", 650, 450)
        self.current_date = datetime.now()
        self.create_content()
    
    def create_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Navigation
        nav_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        nav_frame.pack(fill=tk.X, pady=(0, 8))
        
        prev_btn = tk.Button(nav_frame, text="◀", command=self.prev_month,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2",
                            font=("Segoe UI", 11))
        prev_btn.pack(side=tk.LEFT)
        
        self.month_label = tk.Label(nav_frame, 
                                    text=self.current_date.strftime("%B %Y"),
                                    bg=self.bg_color, font=("Segoe UI", 13, "bold"))
        self.month_label.pack(side=tk.LEFT, expand=True)
        
        next_btn = tk.Button(nav_frame, text="▶", command=self.next_month,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2",
                            font=("Segoe UI", 11))
        next_btn.pack(side=tk.RIGHT)
        
        this_month_btn = tk.Button(nav_frame, text="This Month", command=self.goto_this_month,
                                   bg="#90EE90", cursor="hand2", font=("Segoe UI", 9))
        this_month_btn.pack(side=tk.RIGHT, padx=5)
        
        # Calendar grid
        grid_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        grid_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure columns
        for i in range(7):
            grid_frame.columnconfigure(i, weight=1, uniform="day")
        
        # Day headers with full names
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for i, day in enumerate(days):
            display = day if self.expanded else day[:3]
            lbl = tk.Label(grid_frame, text=display, bg=self.darken_color(self.bg_color, 0.8),
                          font=("Segoe UI", 9, "bold"), relief=tk.RIDGE)
            lbl.grid(row=0, column=i, sticky="nsew", padx=1, pady=1)
        
        # Calendar days
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(self.current_date.year, self.current_date.month)
        today = datetime.now()
        
        for row_idx, week in enumerate(month_days):
            grid_frame.rowconfigure(row_idx + 1, weight=1)
            for col_idx, day in enumerate(week):
                if day == 0:
                    cell = tk.Frame(grid_frame, bg="#F0F0F0", relief=tk.FLAT)
                else:
                    date_str = f"{self.current_date.year}-{self.current_date.month:02d}-{day:02d}"
                    
                    is_today = (day == today.day and 
                               self.current_date.month == today.month and
                               self.current_date.year == today.year)
                    
                    cell_bg = "#FFD700" if is_today else "white"
                    cell = tk.Frame(grid_frame, bg=cell_bg, relief=tk.RIDGE, bd=1)
                    
                    # Day number
                    day_lbl = tk.Label(cell, text=str(day), bg=cell_bg, 
                                      font=("Segoe UI", 9, "bold"), anchor="nw")
                    day_lbl.pack(fill=tk.X, padx=2)
                    
                    # Mini text area for notes
                    text = tk.Text(cell, font=("Segoe UI", 7), wrap=tk.WORD, 
                                  height=3 if self.expanded else 2, width=8, 
                                  relief=tk.FLAT, bg=cell_bg)
                    text.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 2))
                    
                    content = data_manager.data.get("monthly_plans", {}).get(date_str, "")
                    text.insert("1.0", content)
                    text.bind("<FocusOut>", lambda e, d=date_str, t=text: self.save_day(d, t))
                
                cell.grid(row=row_idx + 1, column=col_idx, sticky="nsew", padx=1, pady=1)
    
    def save_day(self, date_str, text_widget):
        if "monthly_plans" not in data_manager.data:
            data_manager.data["monthly_plans"] = {}
        content = text_widget.get("1.0", tk.END).strip()
        if content:
            data_manager.data["monthly_plans"][date_str] = content
        elif date_str in data_manager.data["monthly_plans"]:
            del data_manager.data["monthly_plans"][date_str]
        data_manager.save_data()
    
    def prev_month(self):
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year-1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month-1)
        self.create_content()
    
    def next_month(self):
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year+1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month+1)
        self.create_content()
    
    def goto_this_month(self):
        self.current_date = datetime.now()
        self.create_content()
    
    def update_content(self):
        self.create_content()

# ============== POMODORO TIMER WIDGET ==============
class PomodoroWidget(BaseWidget):
    def __init__(self, master):
        super().__init__(master, "pomodoro", "🍅 Pomodoro Timer", 300, 220)
        
        self.settings = data_manager.data.get("pomodoro_settings", {"focus": 25, "break": 5})
        self.is_running = False
        self.is_break = False
        self.time_left = self.settings["focus"] * 60
        self.sessions_today = self.get_today_sessions()
        self.timer_thread = None
        
        self.create_content()
    
    def get_today_sessions(self):
        today = datetime.now().strftime("%Y-%m-%d")
        return data_manager.data.get("pomodoro_history", {}).get(today, 0)
    
    def create_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Timer display
        timer_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        timer_frame.pack(pady=10)
        
        self.timer_label = tk.Label(
            timer_frame, text=self.format_time(self.time_left),
            font=("Segoe UI", 42, "bold"), bg=self.bg_color
        )
        self.timer_label.pack()
        
        # Mode label
        mode_color = "#FF6347" if not self.is_break else "#32CD32"
        self.mode_label = tk.Label(
            self.content_frame, 
            text="🎯 FOCUS TIME" if not self.is_break else "☕ BREAK TIME",
            font=("Segoe UI", 11, "bold"), bg=self.bg_color, fg=mode_color
        )
        self.mode_label.pack()
        
        # Control buttons
        btn_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        btn_frame.pack(pady=10)
        
        self.start_btn = tk.Button(
            btn_frame, text="▶ Start" if not self.is_running else "⏸ Pause",
            command=self.toggle_timer, 
            bg="#90EE90" if not self.is_running else "#FFD700", 
            font=("Segoe UI", 10, "bold"), width=10, cursor="hand2"
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        reset_btn = tk.Button(
            btn_frame, text="↺ Reset", command=self.reset_timer,
            bg="#FFB6C1", font=("Segoe UI", 10), width=8, cursor="hand2"
        )
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        skip_btn = tk.Button(
            btn_frame, text="⏭ Skip", command=self.skip_timer,
            bg="#87CEEB", font=("Segoe UI", 10), width=8, cursor="hand2"
        )
        skip_btn.pack(side=tk.LEFT, padx=5)
        
        # Sessions today with visual tomatoes
        sessions_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        sessions_frame.pack(pady=5)
        
        tk.Label(sessions_frame, text="Today: ", bg=self.bg_color, 
                font=("Segoe UI", 10)).pack(side=tk.LEFT)
        
        tomatoes = "🍅" * min(self.sessions_today, 10)
        if self.sessions_today > 10:
            tomatoes += f" +{self.sessions_today - 10}"
        elif self.sessions_today == 0:
            tomatoes = "No sessions yet"
        
        self.sessions_label = tk.Label(
            sessions_frame, text=tomatoes,
            font=("Segoe UI", 10), bg=self.bg_color
        )
        self.sessions_label.pack(side=tk.LEFT)
        
        if self.expanded:
            self.create_expanded_content()
    
    def create_expanded_content(self):
        # Settings frame
        settings_frame = tk.LabelFrame(self.content_frame, text="⚙️ Timer Settings", 
                                       bg=self.bg_color, font=("Segoe UI", 10))
        settings_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # Focus time
        focus_frame = tk.Frame(settings_frame, bg=self.bg_color)
        focus_frame.pack(fill=tk.X, padx=10, pady=8)
        
        tk.Label(focus_frame, text="🎯 Focus Time (min):", bg=self.bg_color,
                font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self.focus_var = tk.StringVar(value=str(self.settings["focus"]))
        focus_spin = tk.Spinbox(focus_frame, from_=1, to=90, width=5,
                                textvariable=self.focus_var, 
                                command=self.update_settings,
                                font=("Segoe UI", 10))
        focus_spin.pack(side=tk.LEFT, padx=10)
        focus_spin.bind("<Return>", lambda e: self.update_settings())
        
        # Break time
        tk.Label(focus_frame, text="☕ Break Time (min):", bg=self.bg_color,
                font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.break_var = tk.StringVar(value=str(self.settings["break"]))
        break_spin = tk.Spinbox(focus_frame, from_=1, to=30, width=5,
                                textvariable=self.break_var, 
                                command=self.update_settings,
                                font=("Segoe UI", 10))
        break_spin.pack(side=tk.LEFT, padx=10)
        break_spin.bind("<Return>", lambda e: self.update_settings())
        
        # History frame
        history_frame = tk.LabelFrame(self.content_frame, text="📊 Last 7 Days",
                                      bg=self.bg_color, font=("Segoe UI", 10))
        history_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        history = data_manager.data.get("pomodoro_history", {})
        max_sessions = max(list(history.values()) + [1])
        
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            sessions = history.get(date, 0)
            display_date = (datetime.now() - timedelta(days=i)).strftime("%a %m/%d")
            
            row = tk.Frame(history_frame, bg=self.bg_color)
            row.pack(fill=tk.X, padx=8, pady=2)
            
            tk.Label(row, text=display_date, bg=self.bg_color, width=8, 
                    anchor="w", font=("Segoe UI", 9)).pack(side=tk.LEFT)
            
            # Progress bar
            bar_frame = tk.Frame(row, bg="#DDDDDD", height=18)
            bar_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            bar_frame.pack_propagate(False)
            
            if sessions > 0:
                fill_pct = (sessions / max_sessions) * 100
                fill = tk.Frame(bar_frame, bg="#FF6347", height=18)
                fill.place(relwidth=fill_pct/100, relheight=1)
            
            tk.Label(row, text=f"{sessions} 🍅", bg=self.bg_color, 
                    font=("Segoe UI", 9), width=6).pack(side=tk.RIGHT)
    
    def format_time(self, seconds):
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"
    
    def toggle_timer(self):
        self.is_running = not self.is_running
        if self.is_running:
            self.start_btn.config(text="⏸ Pause", bg="#FFD700")
            self.run_timer()
        else:
            self.start_btn.config(text="▶ Start", bg="#90EE90")
    
    def run_timer(self):
        if self.is_running and self.time_left > 0:
            self.time_left -= 1
            self.timer_label.config(text=self.format_time(self.time_left))
            self.after(1000, self.run_timer)
        elif self.time_left == 0:
            self.timer_complete()
    
    def timer_complete(self):
        self.is_running = False
        self.start_btn.config(text="▶ Start", bg="#90EE90")
        
        if not self.is_break:
            # Completed a focus session
            self.sessions_today += 1
            today = datetime.now().strftime("%Y-%m-%d")
            if "pomodoro_history" not in data_manager.data:
                data_manager.data["pomodoro_history"] = {}
            data_manager.data["pomodoro_history"][today] = self.sessions_today
            data_manager.save_data()
            
            # Update display
            self.update_sessions_display()
            
            # Switch to break
            self.is_break = True
            self.time_left = self.settings["break"] * 60
            self.mode_label.config(text="☕ BREAK TIME", fg="#32CD32")
            
            # Alert
            self.flash_window()
            messagebox.showinfo("🍅 Pomodoro Complete!", 
                              f"Great work! You've completed {self.sessions_today} session(s) today!\n\nTime for a {self.settings['break']} minute break! ☕")
        else:
            # Completed a break
            self.is_break = False
            self.time_left = self.settings["focus"] * 60
            self.mode_label.config(text="🎯 FOCUS TIME", fg="#FF6347")
            
            self.flash_window()
            messagebox.showinfo("☕ Break Over!", "Break time is over!\n\nReady to focus again? 🎯")
        
        self.timer_label.config(text=self.format_time(self.time_left))
    
    def flash_window(self):
        """Flash the window to get attention"""
        original_color = self.bg_color
        for _ in range(3):
            self.configure(bg="#FF6347")
            self.update()
            time.sleep(0.1)
            self.configure(bg=original_color)
            self.update()
            time.sleep(0.1)
    
    def update_sessions_display(self):
        tomatoes = "🍅" * min(self.sessions_today, 10)
        if self.sessions_today > 10:
            tomatoes += f" +{self.sessions_today - 10}"
        self.sessions_label.config(text=tomatoes)
    
    def skip_timer(self):
        """Skip to the next phase"""
        self.time_left = 0
        self.timer_complete()
    
    def reset_timer(self):
        self.is_running = False
        self.is_break = False
        self.time_left = self.settings["focus"] * 60
        self.start_btn.config(text="▶ Start", bg="#90EE90")
        self.mode_label.config(text="🎯 FOCUS TIME", fg="#FF6347")
        self.timer_label.config(text=self.format_time(self.time_left))
    
    def update_settings(self):
        try:
            new_focus = int(self.focus_var.get())
            new_break = int(self.break_var.get())
            
            if new_focus < 1 or new_focus > 90:
                raise ValueError("Focus time must be 1-90 minutes")
            if new_break < 1 or new_break > 30:
                raise ValueError("Break time must be 1-30 minutes")
            
            self.settings["focus"] = new_focus
            self.settings["break"] = new_break
            data_manager.data["pomodoro_settings"] = self.settings
            data_manager.save_data()
            
            if not self.is_running:
                self.time_left = self.settings["focus" if not self.is_break else "break"] * 60
                self.timer_label.config(text=self.format_time(self.time_left))
        except ValueError as e:
            messagebox.showerror("Invalid Setting", str(e))
    
    def update_content(self):
        self.create_content()

# ============== SYSTEM TRAY ICON (Optional) ==============
class SystemTrayIcon:
    """Simple system tray functionality using a small window"""
    def __init__(self, manager):
        self.manager = manager
        self.icon_window = None
    
    def create_icon(self):
        self.icon_window = tk.Toplevel(self.manager.root)
        self.icon_window.overrideredirect(True)
        self.icon_window.geometry("40x40+0+0")
        self.icon_window.attributes('-topmost', True)
        
        icon_btn = tk.Button(
            self.icon_window, text="🖥️", 
            command=self.manager.show_control_panel,
            font=("Segoe UI", 16), cursor="hand2",
            bg="#4A90D9", fg="white", relief=tk.FLAT
        )
        icon_btn.pack(fill=tk.BOTH, expand=True)
        
        # Right-click menu
        self.menu = tk.Menu(self.icon_window, tearoff=0)
        self.menu.add_command(label="Show Control Panel", command=self.manager.show_control_panel)
        self.menu.add_separator()
        self.menu.add_command(label="Show All Widgets", command=self.manager.show_all_widgets)
        self.menu.add_command(label="Hide All Widgets", command=self.manager.hide_all_widgets)
        self.menu.add_separator()
        self.menu.add_command(label="Exit", command=self.manager.quit_app)
        
        icon_btn.bind("<Button-3>", self.show_menu)
    
    def show_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)
    
    def destroy(self):
        if self.icon_window:
            self.icon_window.destroy()

# ============== MAIN APPLICATION ==============
class WidgetManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🖥️ Desktop Widgets Control Panel")
        self.root.geometry("350x500")
        self.root.configure(bg="#F5F5F5")
        self.root.resizable(True, True)
        
        # Set icon (if available)
        try:
            self.root.iconbitmap(default='')
        except:
            pass
        
        # Create control panel
        self.create_control_panel()
        
        # Create all widgets
        self.widgets = {}
        self.create_widgets()
        
        # System tray icon
        self.tray_icon = None
        
        # Add to startup if not already
        if is_in_startup():
            self.startup_var.set(True)
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
    
    def create_control_panel(self):
        # Header
        header = tk.Frame(self.root, bg="#4A90D9", height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title = tk.Label(header, text="🖥️ Desktop Widgets", 
                        font=("Segoe UI", 16, "bold"), bg="#4A90D9", fg="white")
        title.pack(pady=15)
        
        # Main content with scrollbar
        main_canvas = tk.Canvas(self.root, bg="#F5F5F5", highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        scrollable_frame = tk.Frame(main_canvas, bg="#F5F5F5")
        
        scrollable_frame.bind("<Configure>", 
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Widget toggles
        toggle_frame = tk.LabelFrame(scrollable_frame, text="📌 Show/Hide Widgets", 
                                     bg="#F5F5F5", font=("Segoe UI", 10, "bold"),
                                     padx=10, pady=10)
        toggle_frame.pack(fill=tk.X, padx=15, pady=10)
        
        self.widget_vars = {}
        widget_names = [
            ("calendar", "📅 Calendar"),
            ("todo", "✅ To-Do List"),
            ("day_planner", "📋 Day Planner"),
            ("weekly_planner", "📆 Weekly Planner"),
            ("monthly_planner", "🗓️ Monthly Planner"),
            ("pomodoro", "🍅 Pomodoro Timer")
        ]
        
        for key, name in widget_names:
            var = tk.BooleanVar(value=True)
            self.widget_vars[key] = var
            
            row = tk.Frame(toggle_frame, bg="#F5F5F5")
            row.pack(fill=tk.X, pady=3)
            
            cb = tk.Checkbutton(row, text=name, variable=var,
                               bg="#F5F5F5", font=("Segoe UI", 10),
                               command=lambda k=key: self.toggle_widget(k),
                               activebackground="#F5F5F5", cursor="hand2")
            cb.pack(side=tk.LEFT)
        
        # Quick actions
        actions_frame = tk.LabelFrame(scrollable_frame, text="⚡ Quick Actions", 
                                      bg="#F5F5F5", font=("Segoe UI", 10, "bold"),
                                      padx=10, pady=10)
        actions_frame.pack(fill=tk.X, padx=15, pady=10)
        
        btn_style = {"font": ("Segoe UI", 9), "cursor": "hand2", "width": 15}
        
        show_all_btn = tk.Button(actions_frame, text="👁️ Show All Widgets",
                                command=self.show_all_widgets, bg="#90EE90", **btn_style)
        show_all_btn.pack(pady=3)
        
        hide_all_btn = tk.Button(actions_frame, text="🙈 Hide All Widgets",
                                command=self.hide_all_widgets, bg="#FFB6C1", **btn_style)
        hide_all_btn.pack(pady=3)
        
        reset_btn = tk.Button(actions_frame, text="↺ Reset Positions",
                             command=self.reset_positions, bg="#87CEEB", **btn_style)
        reset_btn.pack(pady=3)
        
        # Options
        options_frame = tk.LabelFrame(scrollable_frame, text="⚙️ Options", 
                                      bg="#F5F5F5", font=("Segoe UI", 10, "bold"),
                                      padx=10, pady=10)
        options_frame.pack(fill=tk.X, padx=15, pady=10)
        
        self.startup_var = tk.BooleanVar(value=False)
        startup_cb = tk.Checkbutton(options_frame, text="🚀 Start with Windows",
                                   variable=self.startup_var, bg="#F5F5F5",
                                   command=self.toggle_startup, font=("Segoe UI", 10),
                                   activebackground="#F5F5F5", cursor="hand2")
        startup_cb.pack(anchor="w", pady=3)
        
        # Bottom buttons
        bottom_frame = tk.Frame(scrollable_frame, bg="#F5F5F5")
        bottom_frame.pack(fill=tk.X, padx=15, pady=15)
        
        minimize_btn = tk.Button(bottom_frame, text="➖ Minimize to Corner",
                                command=self.minimize_to_tray, bg="#4A90D9", 
                                fg="white", font=("Segoe UI", 10), cursor="hand2")
        minimize_btn.pack(fill=tk.X, pady=3)
        
        quit_btn = tk.Button(bottom_frame, text="✕ Quit Application",
                            command=self.quit_app, bg="#FF6B6B", 
                            fg="white", font=("Segoe UI", 10), cursor="hand2")
        quit_btn.pack(fill=tk.X, pady=3)
        
        # Info
        info = tk.Label(scrollable_frame, 
                       text="💡 Tip: Widgets stay on desktop behind other apps.\n"
                            "Drag title bar to move, drag corner to resize.\n"
                            "Click 🎨 to change colors, ⬇ to expand.",
                       bg="#F5F5F5", font=("Segoe UI", 9), fg="#666666",
                       justify=tk.LEFT)
        info.pack(pady=10, padx=15)
    
    def create_widgets(self):
        self.widgets["calendar"] = CalendarWidget(self.root)
        self.widgets["todo"] = TodoWidget(self.root)
        self.widgets["day_planner"] = DayPlannerWidget(self.root)
        self.widgets["weekly_planner"] = WeeklyPlannerWidget(self.root)
        self.widgets["monthly_planner"] = MonthlyPlannerWidget(self.root)
        self.widgets["pomodoro"] = PomodoroWidget(self.root)
        
        # Position widgets if no saved positions
        if not data_manager.config.get("positions"):
            self.arrange_widgets()
    
    def arrange_widgets(self):
        """Arrange widgets in a grid on the screen"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        positions = {
            "calendar": (screen_width - 320, 30),
            "todo": (screen_width - 320, 420),
            "day_planner": (screen_width - 640, 30),
            "weekly_planner": (30, 30),
            "monthly_planner": (30, 450),
            "pomodoro": (screen_width - 320, 720)
        }
        
        for key, widget in self.widgets.items():
            if key in positions:
                x, y = positions[key]
                # Make sure widget stays on screen
                x = min(x, screen_width - 100)
                y = min(y, screen_height - 100)
                widget.geometry(f"+{x}+{y}")
    
    def toggle_widget(self, key):
        if self.widget_vars[key].get():
            self.widgets[key].show_widget()
        else:
            self.widgets[key].hide_widget()
    
    def show_all_widgets(self):
        for key, widget in self.widgets.items():
            widget.show_widget()
            self.widget_vars[key].set(True)
    
    def hide_all_widgets(self):
        for key, widget in self.widgets.items():
            widget.hide_widget()
            self.widget_vars[key].set(False)
    
    def toggle_startup(self):
        if self.startup_var.get():
            if add_to_startup():
                messagebox.showinfo("Success", "Application will start with Windows!")
            else:
                messagebox.showerror("Error", "Failed to add to startup.")
                self.startup_var.set(False)
        else:
            remove_from_startup()
    
    def reset_positions(self):
        if messagebox.askyesno("Confirm", "Reset all widget positions?"):
            data_manager.config["positions"] = {}
            data_manager.config["sizes"] = {}
            data_manager.save_config()
            self.arrange_widgets()
    
    def minimize_to_tray(self):
        self.root.withdraw()
        
        # Create small floating button in corner
        if self.tray_icon:
            self.tray_icon.destroy()
        
        self.tray_icon = SystemTrayIcon(self)
        self.tray_icon.create_icon()
    
    def show_control_panel(self):
        if self.tray_icon:
            self.tray_icon.destroy()
            self.tray_icon = None
        self.root.deiconify()
        self.root.lift()
    
    def quit_app(self):
        if messagebox.askyesno("Quit", "Are you sure you want to quit?\n\nAll widgets will close."):
            data_manager.save_data()
            data_manager.save_config()
            self.root.quit()
            self.root.destroy()
    
    def run(self):
        self.root.mainloop()

# ============== MAIN ==============
if __name__ == "__main__":
    print("Starting Desktop Widgets...")
    print(f"Data file: {DATA_FILE}")
    print(f"Config file: {CONFIG_FILE}")
    
    app = WidgetManager()
    app.run()
