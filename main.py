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
import subprocess

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
        with open(DATA_FILE, 'w') as f:
            json.dump(self.data, f, indent=2)
    
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
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)

data_manager = DataManager()

# ============== DESKTOP INTEGRATION (Windows) ==============
def make_desktop_widget(window):
    """Make window stick to desktop on Windows"""
    if not WINDOWS:
        return
    
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        
        # Set extended window style to tool window (no taskbar icon)
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_NOACTIVATE = 0x08000000
        
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        
        # Send window to bottom (above desktop, below other windows)
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
                hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
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
            time.sleep(0.5)
    
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
        
        # Get the path to this script
        script_path = os.path.abspath(sys.argv[0])
        python_path = sys.executable
        command = f'"{python_path}" "{script_path}"'
        
        winreg.SetValueEx(key, "DesktopWidgets", 0, winreg.REG_SZ, command)
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

# ============== BASE WIDGET CLASS ==============
class BaseWidget(tk.Toplevel):
    def __init__(self, master, widget_name, title, min_width=250, min_height=200):
        super().__init__(master)
        
        self.widget_name = widget_name
        self.min_width = min_width
        self.min_height = min_height
        self.expanded = data_manager.config.get("expanded", {}).get(widget_name, False)
        
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
        
        if pos:
            self.geometry(f"+{pos[0]}+{pos[1]}")
        if size:
            self.geometry(f"{size[0]}x{size[1]}")
        else:
            self.geometry(f"{min_width}x{min_height}")
        
        self.minsize(min_width, min_height)
        
        # Create main container
        self.main_frame = tk.Frame(self, bg=self.bg_color)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Title bar
        self.create_title_bar(title)
        
        # Content area
        self.content_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Resize grip
        self.create_resize_grip()
        
        # Make widget stick to desktop
        self.after(100, lambda: make_desktop_widget(self))
        self.after(200, lambda: send_to_desktop_level(self))
        
        # Bind events
        self.bind("<Configure>", self.on_configure)
        
        # Border
        self.configure(highlightbackground="#888888", highlightthickness=1)
    
    def create_title_bar(self, title):
        title_bar = tk.Frame(self.main_frame, bg=self.darken_color(self.bg_color, 0.9))
        title_bar.pack(fill=tk.X)
        
        # Drag functionality
        title_bar.bind("<Button-1>", self.start_drag)
        title_bar.bind("<B1-Motion>", self.on_drag)
        
        # Title label
        title_label = tk.Label(
            title_bar, text=title, bg=self.darken_color(self.bg_color, 0.9),
            font=("Arial", 10, "bold"), fg="#333333"
        )
        title_label.pack(side=tk.LEFT, padx=5, pady=3)
        title_label.bind("<Button-1>", self.start_drag)
        title_label.bind("<B1-Motion>", self.on_drag)
        
        # Buttons frame
        btn_frame = tk.Frame(title_bar, bg=self.darken_color(self.bg_color, 0.9))
        btn_frame.pack(side=tk.RIGHT)
        
        # Color button
        color_btn = tk.Button(
            btn_frame, text="🎨", font=("Arial", 8), relief=tk.FLAT,
            bg=self.darken_color(self.bg_color, 0.9), command=self.change_color,
            width=2, cursor="hand2"
        )
        color_btn.pack(side=tk.LEFT, padx=1)
        
        # Expand/Collapse button
        self.expand_btn = tk.Button(
            btn_frame, text="⬇" if not self.expanded else "⬆", font=("Arial", 8),
            relief=tk.FLAT, bg=self.darken_color(self.bg_color, 0.9),
            command=self.toggle_expand, width=2, cursor="hand2"
        )
        self.expand_btn.pack(side=tk.LEFT, padx=1)
        
        # Close button
        close_btn = tk.Button(
            btn_frame, text="✕", font=("Arial", 8), relief=tk.FLAT,
            bg=self.darken_color(self.bg_color, 0.9), fg="#CC0000",
            command=self.hide_widget, width=2, cursor="hand2"
        )
        close_btn.pack(side=tk.LEFT, padx=1)
    
    def create_resize_grip(self):
        grip = tk.Label(self.main_frame, text="◢", bg=self.bg_color, 
                       fg="#888888", cursor="bottom_right_corner")
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
        self.save_position()
    
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
        self.save_size()
    
    def on_configure(self, event):
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
        color = colorchooser.askcolor(title=f"Choose color for {self.widget_name}")[1]
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
        for widget in self.winfo_children():
            try:
                widget.configure(bg=color)
            except:
                pass
    
    def toggle_expand(self):
        self.expanded = not self.expanded
        if "expanded" not in data_manager.config:
            data_manager.config["expanded"] = {}
        data_manager.config["expanded"][self.widget_name] = self.expanded
        data_manager.save_config()
        
        self.expand_btn.config(text="⬆" if self.expanded else "⬇")
        self.update_content()
    
    def update_content(self):
        """Override in subclasses"""
        pass
    
    def hide_widget(self):
        self.withdraw()
    
    def show_widget(self):
        self.deiconify()
    
    def darken_color(self, hex_color, factor=0.9):
        """Darken a hex color"""
        hex_color = hex_color.lstrip('#')
        r = int(int(hex_color[0:2], 16) * factor)
        g = int(int(hex_color[2:4], 16) * factor)
        b = int(int(hex_color[4:6], 16) * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

# ============== CALENDAR WIDGET ==============
class CalendarWidget(BaseWidget):
    def __init__(self, master):
        super().__init__(master, "calendar", "📅 Calendar", 280, 320)
        self.current_date = datetime.now()
        self.selected_date = None
        self.create_content()
    
    def create_content(self):
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Navigation
        nav_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        nav_frame.pack(fill=tk.X, pady=(0, 5))
        
        prev_btn = tk.Button(nav_frame, text="◀", command=self.prev_month,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2")
        prev_btn.pack(side=tk.LEFT)
        
        self.month_label = tk.Label(
            nav_frame, text=self.current_date.strftime("%B %Y"),
            bg=self.bg_color, font=("Arial", 11, "bold")
        )
        self.month_label.pack(side=tk.LEFT, expand=True)
        
        next_btn = tk.Button(nav_frame, text="▶", command=self.next_month,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2")
        next_btn.pack(side=tk.RIGHT)
        
        # Days header
        days_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        days_frame.pack(fill=tk.X)
        
        days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for day in days:
            lbl = tk.Label(days_frame, text=day, bg=self.bg_color, 
                          font=("Arial", 9, "bold"), width=4)
            lbl.pack(side=tk.LEFT, expand=True)
        
        # Calendar grid
        self.cal_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        self.cal_frame.pack(fill=tk.BOTH, expand=True)
        
        self.update_calendar()
        
        # Event display (expanded mode)
        if self.expanded:
            self.create_event_section()
    
    def create_event_section(self):
        event_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        event_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        tk.Label(event_frame, text="Events:", bg=self.bg_color, 
                font=("Arial", 10, "bold")).pack(anchor="w")
        
        self.event_listbox = tk.Listbox(event_frame, height=4, font=("Arial", 9))
        self.event_listbox.pack(fill=tk.BOTH, expand=True)
        
        btn_frame = tk.Frame(event_frame, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        add_btn = tk.Button(btn_frame, text="+ Add Event", command=self.add_event,
                           bg="#90EE90", cursor="hand2", font=("Arial", 9))
        add_btn.pack(side=tk.LEFT, padx=2)
        
        del_btn = tk.Button(btn_frame, text="- Delete", command=self.delete_event,
                           bg="#FFB6C1", cursor="hand2", font=("Arial", 9))
        del_btn.pack(side=tk.LEFT, padx=2)
        
        self.load_events()
    
    def update_calendar(self):
        for widget in self.cal_frame.winfo_children():
            widget.destroy()
        
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(
            self.current_date.year, self.current_date.month
        )
        
        today = datetime.now()
        
        for week in month_days:
            week_frame = tk.Frame(self.cal_frame, bg=self.bg_color)
            week_frame.pack(fill=tk.X)
            
            for day in week:
                if day == 0:
                    lbl = tk.Label(week_frame, text="", bg=self.bg_color, width=4, height=2)
                else:
                    date_key = f"{self.current_date.year}-{self.current_date.month:02d}-{day:02d}"
                    has_event = date_key in data_manager.data.get("calendar_events", {})
                    
                    bg = self.bg_color
                    fg = "#000000"
                    
                    # Highlight today
                    if (day == today.day and 
                        self.current_date.month == today.month and 
                        self.current_date.year == today.year):
                        bg = "#FFD700"
                    
                    # Event indicator
                    text = str(day)
                    if has_event:
                        text = f"{day}•"
                    
                    lbl = tk.Label(
                        week_frame, text=text, bg=bg, fg=fg, width=4, height=2,
                        relief=tk.RIDGE if has_event else tk.FLAT,
                        cursor="hand2", font=("Arial", 9)
                    )
                    lbl.bind("<Button-1>", lambda e, d=day: self.select_date(d))
                
                lbl.pack(side=tk.LEFT, expand=True, padx=1, pady=1)
        
        self.month_label.config(text=self.current_date.strftime("%B %Y"))
    
    def select_date(self, day):
        self.selected_date = f"{self.current_date.year}-{self.current_date.month:02d}-{day:02d}"
        if self.expanded:
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
        if not self.selected_date:
            messagebox.showinfo("Info", "Please select a date first")
            return
        
        event = simpledialog.askstring("Add Event", f"Event for {self.selected_date}:")
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
        if not hasattr(self, 'event_listbox'):
            return
        selection = self.event_listbox.curselection()
        if selection and self.selected_date:
            idx = selection[0]
            events = data_manager.data.get("calendar_events", {}).get(self.selected_date, [])
            if idx < len(events):
                events.pop(idx)
                if not events:
                    del data_manager.data["calendar_events"][self.selected_date]
                data_manager.save_data()
                self.load_events()
                self.update_calendar()
    
    def load_events(self):
        if not hasattr(self, 'event_listbox'):
            return
        self.event_listbox.delete(0, tk.END)
        if self.selected_date:
            events = data_manager.data.get("calendar_events", {}).get(self.selected_date, [])
            for event in events:
                self.event_listbox.insert(tk.END, event)
    
    def update_content(self):
        self.create_content()

# ============== TODO LIST WIDGET ==============
class TodoWidget(BaseWidget):
    def __init__(self, master):
        super().__init__(master, "todo", "✅ To-Do List", 250, 250)
        self.create_content()
    
    def create_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Input frame
        input_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        input_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.todo_entry = tk.Entry(input_frame, font=("Arial", 10))
        self.todo_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.todo_entry.bind("<Return>", lambda e: self.add_todo())
        
        add_btn = tk.Button(input_frame, text="+", command=self.add_todo,
                           bg="#90EE90", width=3, cursor="hand2")
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Todo list with scrollbar
        list_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.todo_canvas = tk.Canvas(list_frame, bg=self.bg_color, 
                                     yscrollcommand=scrollbar.set)
        self.todo_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.todo_canvas.yview)
        
        self.todo_inner_frame = tk.Frame(self.todo_canvas, bg=self.bg_color)
        self.todo_canvas.create_window((0, 0), window=self.todo_inner_frame, anchor="nw")
        
        self.todo_inner_frame.bind("<Configure>", 
            lambda e: self.todo_canvas.configure(scrollregion=self.todo_canvas.bbox("all")))
        
        self.load_todos()
        
        if self.expanded:
            self.create_expanded_options()
    
    def create_expanded_options(self):
        opt_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        opt_frame.pack(fill=tk.X, pady=(10, 0))
        
        clear_done_btn = tk.Button(opt_frame, text="Clear Completed", 
                                   command=self.clear_completed,
                                   bg="#FFB6C1", cursor="hand2", font=("Arial", 9))
        clear_done_btn.pack(side=tk.LEFT)
        
        clear_all_btn = tk.Button(opt_frame, text="Clear All", 
                                  command=self.clear_all,
                                  bg="#FF6B6B", cursor="hand2", font=("Arial", 9))
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
                command=lambda idx=i, v=var: self.toggle_todo(idx, v)
            )
            cb.pack(side=tk.LEFT)
            
            text = todo["text"]
            fg = "#888888" if todo["done"] else "#000000"
            font = ("Arial", 10, "overstrike") if todo["done"] else ("Arial", 10)
            
            lbl = tk.Label(todo_frame, text=text, bg=self.bg_color, fg=fg, 
                          font=font, anchor="w")
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            del_btn = tk.Button(todo_frame, text="✕", command=lambda idx=i: self.delete_todo(idx),
                               bg=self.bg_color, fg="#CC0000", relief=tk.FLAT,
                               cursor="hand2", font=("Arial", 8))
            del_btn.pack(side=tk.RIGHT)
    
    def toggle_todo(self, idx, var):
        data_manager.data["todos"][idx]["done"] = var.get()
        data_manager.save_data()
        self.load_todos()
    
    def delete_todo(self, idx):
        data_manager.data["todos"].pop(idx)
        data_manager.save_data()
        self.load_todos()
    
    def clear_completed(self):
        data_manager.data["todos"] = [t for t in data_manager.data.get("todos", []) if not t["done"]]
        data_manager.save_data()
        self.load_todos()
    
    def clear_all(self):
        if messagebox.askyesno("Confirm", "Clear all todos?"):
            data_manager.data["todos"] = []
            data_manager.save_data()
            self.load_todos()
    
    def update_content(self):
        self.create_content()

# ============== DAY PLANNER WIDGET ==============
class DayPlannerWidget(BaseWidget):
    def __init__(self, master):
        super().__init__(master, "day_planner", "📋 Day Planner", 280, 350)
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.create_content()
    
    def create_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Date navigation
        nav_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        nav_frame.pack(fill=tk.X, pady=(0, 5))
        
        prev_btn = tk.Button(nav_frame, text="◀", command=self.prev_day,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2")
        prev_btn.pack(side=tk.LEFT)
        
        self.date_label = tk.Label(nav_frame, text=self.current_date,
                                   bg=self.bg_color, font=("Arial", 11, "bold"))
        self.date_label.pack(side=tk.LEFT, expand=True)
        
        next_btn = tk.Button(nav_frame, text="▶", command=self.next_day,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2")
        next_btn.pack(side=tk.RIGHT)
        
        today_btn = tk.Button(nav_frame, text="Today", command=self.goto_today,
                             bg="#90EE90", cursor="hand2", font=("Arial", 9))
        today_btn.pack(side=tk.RIGHT, padx=5)
        
        # Time slots
        slots_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        slots_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollable area
        canvas = tk.Canvas(slots_frame, bg=self.bg_color)
        scrollbar = tk.Scrollbar(slots_frame, orient="vertical", command=canvas.yview)
        self.slots_inner = tk.Frame(canvas, bg=self.bg_color)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0, 0), window=self.slots_inner, anchor="nw")
        
        self.slots_inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Create time slots
        hours = range(6, 23) if self.expanded else range(8, 18)
        for hour in hours:
            self.create_time_slot(hour)
    
    def create_time_slot(self, hour):
        slot_frame = tk.Frame(self.slots_inner, bg=self.bg_color)
        slot_frame.pack(fill=tk.X, pady=1)
        
        time_label = tk.Label(slot_frame, text=f"{hour:02d}:00", 
                             bg=self.bg_color, font=("Arial", 9), width=6)
        time_label.pack(side=tk.LEFT)
        
        key = f"{self.current_date}_{hour}"
        current_text = data_manager.data.get("day_plans", {}).get(key, "")
        
        entry = tk.Entry(slot_frame, font=("Arial", 9))
        entry.insert(0, current_text)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        entry.bind("<FocusOut>", lambda e, k=key, en=entry: self.save_slot(k, en))
        entry.bind("<Return>", lambda e, k=key, en=entry: self.save_slot(k, en))
    
    def save_slot(self, key, entry):
        if "day_plans" not in data_manager.data:
            data_manager.data["day_plans"] = {}
        text = entry.get().strip()
        if text:
            data_manager.data["day_plans"][key] = text
        elif key in data_manager.data["day_plans"]:
            del data_manager.data["day_plans"][key]
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
        super().__init__(master, "weekly_planner", "📆 Weekly Planner", 500, 350)
        self.current_week_start = self.get_week_start(datetime.now())
        self.create_content()
    
    def get_week_start(self, date):
        return date - timedelta(days=date.weekday())
    
    def create_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Navigation
        nav_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        nav_frame.pack(fill=tk.X, pady=(0, 5))
        
        prev_btn = tk.Button(nav_frame, text="◀ Prev Week", command=self.prev_week,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2")
        prev_btn.pack(side=tk.LEFT)
        
        week_end = self.current_week_start + timedelta(days=6)
        week_text = f"{self.current_week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"
        self.week_label = tk.Label(nav_frame, text=week_text,
                                   bg=self.bg_color, font=("Arial", 11, "bold"))
        self.week_label.pack(side=tk.LEFT, expand=True)
        
        next_btn = tk.Button(nav_frame, text="Next Week ▶", command=self.next_week,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2")
        next_btn.pack(side=tk.RIGHT)
        
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
            
            # Header
            header_bg = "#FFD700" if day_date.date() == today else self.darken_color(self.bg_color, 0.9)
            header = tk.Label(grid_frame, text=f"{day_name[:3]}\n{day_date.day}",
                            bg=header_bg, font=("Arial", 9, "bold"), relief=tk.RIDGE)
            header.grid(row=0, column=i, sticky="nsew", padx=1, pady=1)
            
            # Content area
            day_frame = tk.Frame(grid_frame, bg="white", relief=tk.SUNKEN, bd=1)
            day_frame.grid(row=1, column=i, sticky="nsew", padx=1, pady=1)
            
            # Text widget for plans
            text = tk.Text(day_frame, font=("Arial", 8), wrap=tk.WORD, height=8, width=10)
            text.pack(fill=tk.BOTH, expand=True)
            
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
    
    def update_content(self):
        self.create_content()

# ============== MONTHLY PLANNER WIDGET ==============
class MonthlyPlannerWidget(BaseWidget):
    def __init__(self, master):
        super().__init__(master, "monthly_planner", "🗓️ Monthly Planner", 550, 400)
        self.current_date = datetime.now()
        self.create_content()
    
    def create_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Navigation
        nav_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        nav_frame.pack(fill=tk.X, pady=(0, 5))
        
        prev_btn = tk.Button(nav_frame, text="◀", command=self.prev_month,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2")
        prev_btn.pack(side=tk.LEFT)
        
        self.month_label = tk.Label(nav_frame, 
                                    text=self.current_date.strftime("%B %Y"),
                                    bg=self.bg_color, font=("Arial", 12, "bold"))
        self.month_label.pack(side=tk.LEFT, expand=True)
        
        next_btn = tk.Button(nav_frame, text="▶", command=self.next_month,
                            bg=self.bg_color, relief=tk.FLAT, cursor="hand2")
        next_btn.pack(side=tk.RIGHT)
        
        # Calendar grid
        grid_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        grid_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure columns
        for i in range(7):
            grid_frame.columnconfigure(i, weight=1, uniform="day")
        
        # Day headers
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day in enumerate(days):
            lbl = tk.Label(grid_frame, text=day, bg=self.darken_color(self.bg_color, 0.85),
                          font=("Arial", 9, "bold"))
            lbl.grid(row=0, column=i, sticky="nsew", padx=1, pady=1)
        
        # Calendar days
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(self.current_date.year, self.current_date.month)
        today = datetime.now()
        
        for row_idx, week in enumerate(month_days):
            grid_frame.rowconfigure(row_idx + 1, weight=1)
            for col_idx, day in enumerate(week):
                if day == 0:
                    cell = tk.Frame(grid_frame, bg="#EEEEEE")
                else:
                    date_str = f"{self.current_date.year}-{self.current_date.month:02d}-{day:02d}"
                    
                    is_today = (day == today.day and 
                               self.current_date.month == today.month and
                               self.current_date.year == today.year)
                    
                    cell_bg = "#FFD700" if is_today else "white"
                    cell = tk.Frame(grid_frame, bg=cell_bg, relief=tk.SUNKEN, bd=1)
                    
                    # Day number
                    day_lbl = tk.Label(cell, text=str(day), bg=cell_bg, 
                                      font=("Arial", 9, "bold"), anchor="nw")
                    day_lbl.pack(fill=tk.X)
                    
                    # Mini text area for notes
                    text = tk.Text(cell, font=("Arial", 7), wrap=tk.WORD, height=2, width=8)
                    text.pack(fill=tk.BOTH, expand=True)
                    
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
    
    def update_content(self):
        self.create_content()

# ============== POMODORO TIMER WIDGET ==============
class PomodoroWidget(BaseWidget):
    def __init__(self, master):
        super().__init__(master, "pomodoro", "🍅 Pomodoro Timer", 280, 200)
        
        self.settings = data_manager.data.get("pomodoro_settings", {"focus": 25, "break": 5})
        self.is_running = False
        self.is_break = False
        self.time_left = self.settings["focus"] * 60
        self.sessions_today = self.get_today_sessions()
        
        self.create_content()
    
    def get_today_sessions(self):
        today = datetime.now().strftime("%Y-%m-%d")
        return data_manager.data.get("pomodoro_history", {}).get(today, 0)
    
    def create_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Timer display
        self.timer_label = tk.Label(
            self.content_frame, text=self.format_time(self.time_left),
            font=("Arial", 36, "bold"), bg=self.bg_color
        )
        self.timer_label.pack(pady=10)
        
        # Mode label
        self.mode_label = tk.Label(
            self.content_frame, 
            text="🎯 Focus Time" if not self.is_break else "☕ Break Time",
            font=("Arial", 12), bg=self.bg_color
        )
        self.mode_label.pack()
        
        # Control buttons
        btn_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        btn_frame.pack(pady=10)
        
        self.start_btn = tk.Button(
            btn_frame, text="▶ Start" if not self.is_running else "⏸ Pause",
            command=self.toggle_timer, bg="#90EE90", 
            font=("Arial", 10), width=8, cursor="hand2"
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        reset_btn = tk.Button(
            btn_frame, text="↺ Reset", command=self.reset_timer,
            bg="#FFB6C1", font=("Arial", 10), width=8, cursor="hand2"
        )
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        # Sessions today
        self.sessions_label = tk.Label(
            self.content_frame, 
            text=f"Sessions today: {self.sessions_today} 🍅",
            font=("Arial", 10), bg=self.bg_color
        )
        self.sessions_label.pack()
        
        if self.expanded:
            self.create_expanded_content()
    
    def create_expanded_content(self):
        # Settings frame
        settings_frame = tk.LabelFrame(self.content_frame, text="Settings", 
                                       bg=self.bg_color, font=("Arial", 10))
        settings_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # Focus time
        focus_frame = tk.Frame(settings_frame, bg=self.bg_color)
        focus_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(focus_frame, text="Focus (min):", bg=self.bg_color).pack(side=tk.LEFT)
        self.focus_var = tk.StringVar(value=str(self.settings["focus"]))
        focus_spin = tk.Spinbox(focus_frame, from_=1, to=60, width=5,
                                textvariable=self.focus_var, command=self.update_settings)
        focus_spin.pack(side=tk.LEFT, padx=5)
        
        # Break time
        tk.Label(focus_frame, text="Break (min):", bg=self.bg_color).pack(side=tk.LEFT)
        self.break_var = tk.StringVar(value=str(self.settings["break"]))
        break_spin = tk.Spinbox(focus_frame, from_=1, to=30, width=5,
                                textvariable=self.break_var, command=self.update_settings)
        break_spin.pack(side=tk.LEFT, padx=5)
        
        # History
        history_frame = tk.LabelFrame(self.content_frame, text="History (Last 7 days)",
                                      bg=self.bg_color, font=("Arial", 10))
        history_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        history = data_manager.data.get("pomodoro_history", {})
        
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            sessions = history.get(date, 0)
            display_date = (datetime.now() - timedelta(days=i)).strftime("%a %m/%d")
            
            row = tk.Frame(history_frame, bg=self.bg_color)
            row.pack(fill=tk.X, padx=5, pady=1)
            
            tk.Label(row, text=display_date, bg=self.bg_color, width=10, 
                    anchor="w").pack(side=tk.LEFT)
            
            # Progress bar
            bar_frame = tk.Frame(row, bg="#DDDDDD", height=15)
            bar_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            if sessions > 0:
                fill_width = min(sessions * 10, 100)
                fill = tk.Frame(bar_frame, bg="#FF6347", height=15, width=fill_width)
                fill.pack(side=tk.LEFT)
            
            tk.Label(row, text=f"{sessions}🍅", bg=self.bg_color).pack(side=tk.RIGHT)
    
    def format_time(self, seconds):
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"
    
    def toggle_timer(self):
        self.is_running = not self.is_running
        self.start_btn.config(text="⏸ Pause" if self.is_running else "▶ Start")
        if self.is_running:
            self.run_timer()
    
    def run_timer(self):
        if self.is_running and self.time_left > 0:
            self.time_left -= 1
            self.timer_label.config(text=self.format_time(self.time_left))
            self.after(1000, self.run_timer)
        elif self.time_left == 0:
            self.timer_complete()
    
    def timer_complete(self):
        self.is_running = False
        self.start_btn.config(text="▶ Start")
        
        if not self.is_break:
            # Completed a focus session
            self.sessions_today += 1
            today = datetime.now().strftime("%Y-%m-%d")
            if "pomodoro_history" not in data_manager.data:
                data_manager.data["pomodoro_history"] = {}
            data_manager.data["pomodoro_history"][today] = self.sessions_today
            data_manager.save_data()
            
            self.sessions_label.config(text=f"Sessions today: {self.sessions_today} 🍅")
            
            # Switch to break
            self.is_break = True
            self.time_left = self.settings["break"] * 60
            self.mode_label.config(text="☕ Break Time")
            messagebox.showinfo("Pomodoro", "Focus session complete! Take a break! ☕")
        else:
            # Completed a break
            self.is_break = False
            self.time_left = self.settings["focus"] * 60
            self.mode_label.config(text="🎯 Focus Time")
            messagebox.showinfo("Pomodoro", "Break over! Ready to focus! 🎯")
        
        self.timer_label.config(text=self.format_time(self.time_left))
    
    def reset_timer(self):
        self.is_running = False
        self.is_break = False
        self.time_left = self.settings["focus"] * 60
        self.start_btn.config(text="▶ Start")
        self.mode_label.config(text="🎯 Focus Time")
        self.timer_label.config(text=self.format_time(self.time_left))
    
    def update_settings(self):
        try:
            self.settings["focus"] = int(self.focus_var.get())
            self.settings["break"] = int(self.break_var.get())
            data_manager.data["pomodoro_settings"] = self.settings
            data_manager.save_data()
            
            if not self.is_running:
                self.time_left = self.settings["focus" if not self.is_break else "break"] * 60
                self.timer_label.config(text=self.format_time(self.time_left))
        except:
            pass
    
    def update_content(self):
        self.create_content()

# ============== MAIN APPLICATION ==============
class WidgetManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Desktop Widgets Manager")
        self.root.geometry("300x400")
        self.root.configure(bg="#F0F0F0")
        
        # Keep root window small and use it as control panel
        self.create_control_panel()
        
        # Create all widgets
        self.widgets = {}
        self.create_widgets()
        
        # Add to startup
        add_to_startup()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
    
    def create_control_panel(self):
        title = tk.Label(self.root, text="🖥️ Desktop Widgets", 
                        font=("Arial", 14, "bold"), bg="#F0F0F0")
        title.pack(pady=10)
        
        # Widget toggles
        toggle_frame = tk.LabelFrame(self.root, text="Show/Hide Widgets", 
                                     bg="#F0F0F0", font=("Arial", 10))
        toggle_frame.pack(fill=tk.X, padx=10, pady=5)
        
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
            cb = tk.Checkbutton(toggle_frame, text=name, variable=var,
                               bg="#F0F0F0", font=("Arial", 10),
                               command=lambda k=key: self.toggle_widget(k))
            cb.pack(anchor="w", padx=10, pady=2)
        
        # Options
        options_frame = tk.LabelFrame(self.root, text="Options", 
                                      bg="#F0F0F0", font=("Arial", 10))
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.startup_var = tk.BooleanVar(value=True)
        startup_cb = tk.Checkbutton(options_frame, text="Start with Windows",
                                   variable=self.startup_var, bg="#F0F0F0",
                                   command=self.toggle_startup)
        startup_cb.pack(anchor="w", padx=10, pady=2)
        
        # Buttons
        btn_frame = tk.Frame(self.root, bg="#F0F0F0")
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        reset_btn = tk.Button(btn_frame, text="Reset All Positions",
                             command=self.reset_positions, bg="#FFB6C1",
                             cursor="hand2")
        reset_btn.pack(fill=tk.X, pady=2)
        
        minimize_btn = tk.Button(btn_frame, text="Minimize Control Panel",
                                command=self.minimize_to_tray, bg="#87CEEB",
                                cursor="hand2")
        minimize_btn.pack(fill=tk.X, pady=2)
        
        quit_btn = tk.Button(btn_frame, text="Quit Application",
                            command=self.quit_app, bg="#FF6B6B",
                            cursor="hand2")
        quit_btn.pack(fill=tk.X, pady=2)
        
        # Instructions
        info = tk.Label(self.root, text="Widgets will stick to desktop.\n"
                       "Drag title bar to move.\nDrag corner to resize.",
                       bg="#F0F0F0", font=("Arial", 9), fg="#666666")
        info.pack(pady=5)
    
    def create_widgets(self):
        self.widgets["calendar"] = CalendarWidget(self.root)
        self.widgets["todo"] = TodoWidget(self.root)
        self.widgets["day_planner"] = DayPlannerWidget(self.root)
        self.widgets["weekly_planner"] = WeeklyPlannerWidget(self.root)
        self.widgets["monthly_planner"] = MonthlyPlannerWidget(self.root)
        self.widgets["pomodoro"] = PomodoroWidget(self.root)
        
        # Position widgets in a grid initially if no saved positions
        if not data_manager.config.get("positions"):
            self.arrange_widgets()
    
    def arrange_widgets(self):
        """Arrange widgets in a grid on the right side of screen"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        positions = [
            (screen_width - 300, 50),      # Calendar
            (screen_width - 300, 400),     # Todo
            (screen_width - 600, 50),      # Day Planner
            (50, 50),                       # Weekly Planner
            (50, 450),                      # Monthly Planner
            (screen_width - 300, 650)      # Pomodoro
        ]
        
        for i, (key, widget) in enumerate(self.widgets.items()):
            if i < len(positions):
                x, y = positions[i]
                widget.geometry(f"+{x}+{y}")
    
    def toggle_widget(self, key):
        if self.widget_vars[key].get():
            self.widgets[key].show_widget()
        else:
            self.widgets[key].hide_widget()
    
    def toggle_startup(self):
        if self.startup_var.get():
            add_to_startup()
        else:
            remove_from_startup()
    
    def reset_positions(self):
        data_manager.config["positions"] = {}
        data_manager.config["sizes"] = {}
        data_manager.save_config()
        self.arrange_widgets()
    
    def minimize_to_tray(self):
        self.root.withdraw()
        
        # Create small restore button
        restore_window = tk.Toplevel(self.root)
        restore_window.overrideredirect(True)
        restore_window.attributes('-topmost', True)
        restore_window.geometry("30x30+0+0")
        
        restore_btn = tk.Button(restore_window, text="🖥️", 
                               command=lambda: self.restore_panel(restore_window),
                               font=("Arial", 12), cursor="hand2")
        restore_btn.pack(fill=tk.BOTH, expand=True)
    
    def restore_panel(self, restore_window):
        restore_window.destroy()
        self.root.deiconify()
    
    def quit_app(self):
        data_manager.save_data()
        data_manager.save_config()
        self.root.quit()
    
    def run(self):
        self.root.mainloop()

# ============== MAIN ==============
if __name__ == "__main__":
    app = WidgetManager()
    app.run()
