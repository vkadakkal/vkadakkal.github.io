import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
from tkinter import Toplevel, StringVar, OptionMenu
from datetime import datetime
from dateutil.relativedelta import relativedelta

DOMAIN_OPTIONS = ["Analysis", "HW", "MPG"]

class EditableTreeview(ttk.Treeview):
    def __init__(self, parent, save_callback, get_rowinfo_callback, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.bind("<Double-1>", self.on_double_click)
        self.editable_columns = set()
        self.edit_entry = None
        self.edit_item = None
        self.edit_column = None
        self.save_callback = save_callback
        self.get_rowinfo_callback = get_rowinfo_callback

    def on_double_click(self, event):
        region = self.identify_region(event.x, event.y)
        if region == "cell":
            column = self.identify_column(event.x)
            item = self.identify_row(event.y)
            if column in self.editable_columns:
                self.start_edit(item, column)

    def start_edit(self, item, column):
        if self.edit_entry:
            self.edit_entry.destroy()
        value = self.set(item, column)
        x, y, width, height = self.bbox(item, column)
        if width == 0 or height == 0:
            return
        self.tag_configure("editing", background="#e0f0ff")
        self.item(item, tags=("editing",))
        self.edit_entry = tk.Entry(self, bg="#e0f0ff", fg="#000000", font=('Segoe UI', 11), insertbackground='black')
        self.edit_entry.insert(0, value)
        self.edit_entry.place(x=x, y=y, width=width, height=height)
        self.edit_entry.focus_set()
        self.edit_entry.icursor(tk.END)
        def finish_edit(event=None):
            new_value = self.edit_entry.get()
            self.set(self.edit_item, self.edit_column, new_value)
            self.save_callback(self.edit_item, self.edit_column, new_value, self.get_rowinfo_callback(self.edit_item, self.edit_column))
            self.edit_entry.destroy()
            self.edit_entry = None
            self.item(self.edit_item, tags=())
            return new_value
        self.edit_entry.bind("<Return>", finish_edit)
        self.edit_entry.bind("<FocusOut>", finish_edit)
        self.edit_item = item
        self.edit_column = column

class DragFillTreeview(EditableTreeview):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.start_cell = None
        self.drag_data = {"x": 0, "y": 0, "item": None}

    def on_press(self, event):
        region = self.identify_region(event.x, event.y)
        if region == "cell":
            item = self.identify_row(event.y)
            column_id = self.identify_column(event.x)
            cols = self['columns']
            col_index = int(column_id[1:]) - 1
            if 0 <= col_index < len(cols):
                column_name = cols[col_index]
                self.start_cell = (item, column_name)
                self.drag_data["item"] = item
                self.drag_data["column"] = column_name
                self.drag_data["x"] = event.x
                self.drag_data["y"] = event.y
                self.drag_data["value"] = self.set(item, column_name)

    def on_drag(self, event):
        if self.start_cell:
            dx = abs(event.x - self.drag_data["x"])
            dy = abs(event.y - self.drag_data["y"])
            if dx > 5 or dy > 5:
                self.config(cursor="hand2")

    def on_release(self, event):
        if self.start_cell:
            self.config(cursor="")
            region = self.identify_region(event.x, event.y)
            if region == "cell":
                end_item = self.identify_row(event.y)
                column_id = self.identify_column(event.x)
                cols = self['columns']
                col_index = int(column_id[1:]) - 1
                if 0 <= col_index < len(cols):
                    end_column = cols[col_index]
                    self.fill_cells(self.start_cell, (end_item, end_column))
            self.start_cell = None

    def fill_cells(self, start, end):
        start_item, start_col = start
        end_item, end_col = end
        all_items = self.get_children('')
        start_idx = all_items.index(start_item)
        end_idx = all_items.index(end_item)
        cols = self['columns']
        start_col_idx = cols.index(start_col)
        end_col_idx = cols.index(end_col)
        start_value = self.set(start_item, start_col)
        
        for row_idx in range(min(start_idx, end_idx), max(start_idx, end_idx)+1):
            item = all_items[row_idx]
            for col_idx in range(min(start_col_idx, end_col_idx), max(start_col_idx, end_col_idx)+1):
                col_name = cols[col_idx]
                self.set(item, col_name, start_value)
                column_id = '#' + str(col_idx + 1)
                row_info = self.get_rowinfo_callback(item, column_id)
                self.save_callback(item, column_id, start_value, row_info)
                
        # Save data after drag-fill operation
        if hasattr(self.master, 'save_data'):
            self.master.save_data()

class StaffingTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Staffing Demand vs Availability Tracker")
        self.geometry("1200x750")
        self.configure(bg="#23272e")
        self.data_file = "staffing_data.json"
        
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure(
            "Treeview",
            background="#23272e",
            foreground="#ffffff",
            fieldbackground="#23272e",
            rowheight=26,
            font=('Segoe UI', 11),
            borderwidth=2,
            relief="ridge",
        )
        self.style.configure(
            "Treeview.Heading",
            background="#313640",
            foreground="#fffcfc",
            font=('Segoe UI', 10, 'bold'),
            borderwidth=2,
            relief="ridge",
        )
        self.style.configure(
            "red_cell", 
            background="#ff9999", 
            foreground="#000000"
        )
        self.style.configure(
            "blue_cell", 
            background="#9999ff", 
            foreground="#000000"
        )
        self.style.configure(
            "normal_cell", 
            background="#23272e", 
            foreground="#ffffff"
        )
        self.style.map(
            'Treeview',
            background=[('selected', '#0078D7')],
            foreground=[('selected', '#ffffff')]
        )
        self.style.map('TButton', background=[('active', '#555555')])
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)
        
        self.tabs = {}
        tab_names = ["Employees", "Availability", "Demand", "Allocation", "Demand-Alloc", "Alloc-Avail"]
        for name in tab_names:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=name)
            self.tabs[name] = frame
            self.setup_tab_navigation(frame)
        
        self.status_var = tk.StringVar()
        self.status_var.set('Ready')
        self.status_bar = ttk.Frame(self)
        self.status_bar.pack(side='bottom', fill='x', padx=2, pady=1)
        
        ttk.Label(
            self.status_bar, 
            textvariable=self.status_var, 
            relief='sunken', 
            anchor='w',
            background='#3e3e3e',
            foreground='white'
        ).pack(side='left', fill='x', expand=True)
        
        ttk.Button(self.status_bar, text="Config", command=self.open_config).pack(side='right', padx=5)
        
        self.current_month_index = 0
        self.load_data()
        self.setup_tabs()
        self.update_month_headers()
        self.update_status_period()

    def get_month_headers(self):
        base_date = datetime.now() + relativedelta(months=self.current_month_index)
        return [(base_date + relativedelta(months=i)).strftime('%m/%y') for i in range(12)]

    def get_month_keys(self):
        base_date = datetime.now() + relativedelta(months=self.current_month_index)
        return [(base_date + relativedelta(months=i)).strftime('%Y-%m') for i in range(12)]

    def update_month_headers(self):
        months = self.get_month_headers()
        for i in range(12):
            col_name = f"month_{i}"
            for tree in [getattr(self, attr, None) for attr in [
                'avail_tree', 'demand_tree', 'alloc_tree', 'output1_tree', 'output2_tree'
            ]]:
                if tree:
                    tree.heading(col_name, text=months[i])
                    tree.column(col_name, width=50, minwidth=40, anchor='center')

    def update_status_period(self):
        months = self.get_month_headers()
        if months:
            self.status_var.set(f'Viewing period: {months[0]} to {months[-1]}')
        else:
            self.status_var.set('Ready')

    def load_data(self):
        try:
            with open(self.data_file, 'r') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            self.data = {
                "employees": [],
                "availability": {},
                "demand": {},
                "allocation": [],
                "thresholds": {
                    "output1_red": 1.0,
                    "output1_blue": 0.0,
                    "output2_red": 1.2,
                    "output2_blue": 0.8
                }
            }
        finally:
            self.update_status_period()
            
    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)
        self.status_var.set(f'Saved data to {self.data_file}')
        
    def setup_tab_navigation(self, frame):
        nav_frame = ttk.Frame(frame)
        nav_frame.pack(fill='x', padx=5, pady=5)
        ttk.Button(nav_frame, text="<<", command=lambda: self.change_month(-1)).pack(side='left')
        ttk.Button(nav_frame, text=">>", command=lambda: self.change_month(1)).pack(side='right')
        
    def change_month(self, delta):
        self.current_month_index += delta
        self.update_month_headers()
        self.update_all_tabs()
        self.update_status_period()
        
    def setup_tabs(self):
        self.setup_employees_tab()
        self.setup_availability_tab()
        self.setup_demand_tab()
        self.setup_allocation_tab()
        self.setup_output_tabs()
        
    def setup_employees_tab(self):
        frame = self.tabs["Employees"]
        
        columns = ("id", "name", "domain", "manager")
        self.emp_tree = ttk.Treeview(frame, columns=columns, show='headings')
        self.emp_tree.heading("id", text="ID")
        self.emp_tree.column("id", width=50, anchor='w')
        self.emp_tree.heading("name", text="Name")
        self.emp_tree.column("name", width=150, anchor='w')
        self.emp_tree.heading("domain", text="Domain")
        self.emp_tree.column("domain", width=120, anchor='w')
        self.emp_tree.heading("manager", text="Manager")
        self.emp_tree.column("manager", width=120, anchor='w')
        self.emp_tree.pack(fill='both', expand=True, padx=10, pady=10)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(btn_frame, text="Add", command=self.add_employee).pack(side='left')
        ttk.Button(btn_frame, text="Edit", command=self.edit_employee).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Remove", command=self.remove_employee).pack(side='left')
        
        self.update_employees_tab()
        
    def add_employee(self):
        dialog = Toplevel(self)
        dialog.title("Add Employee")
        dialog.geometry("300x150")
        dialog.grab_set()
        
        entries = {}
        fields = [("name", "Name:"), ("manager", "Manager:")]
        
        for i, (key, label) in enumerate(fields):
            ttk.Label(dialog, text=label).grid(row=i, column=0, padx=5, pady=5, sticky='e')
            entry = ttk.Entry(dialog)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky='we')
            entries[key] = entry
            
        ttk.Label(dialog, text="Domain:").grid(row=2, column=0, padx=5, pady=5, sticky='e')
        domain_var = StringVar(dialog)
        domain_combo = ttk.Combobox(dialog, textvariable=domain_var, 
                                   values=DOMAIN_OPTIONS, state="readonly")
        domain_combo.grid(row=2, column=1, padx=5, pady=5, sticky='we')
        domain_combo.current(0)
            
        def save():
            emp_data = {
                "name": entries['name'].get(),
                "manager": entries['manager'].get(),
                "domain": domain_var.get()
            }
            if not all(emp_data.values()):
                messagebox.showerror("Error", "All fields are required")
                return
                
            emp_ids = [int(emp['id']) for emp in self.data['employees']] or [0]
            new_id = str(max(emp_ids) + 1)
            
            self.data['employees'].append({
                "id": new_id,
                "name": emp_data['name'],
                "domain": emp_data['domain'],
                "manager": emp_data['manager']
            })
            self.data['availability'][new_id] = {}
            self.save_data()
            self.update_employees_tab()
            self.update_availability_tab()
            dialog.destroy()
            self.status_var.set(f'Added employee: {emp_data["name"]}')
            
        ttk.Button(dialog, text="Save", command=save).grid(row=3, column=1, sticky='e', padx=5, p极y=10)
        
    def edit_employee(self):
        selected = self.emp_tree.selection()
        if not selected:
            return
            
        item = selected[0]
        emp_id = self.emp_tree.item(item, 'values')[0]
        employee = next(emp for emp in self.data['employees'] if emp['id'] == emp_id)
        
        dialog = Toplevel(self)
        dialog.title("Edit Employee")
        dialog.geometry("300x150")
        dialog.grab_set()
        
        entries = {}
        fields = [("name", "Name:"), ("manager", "Manager:")]
        
        for i, (key, label) in enumerate(fields):
            ttk.Label(dialog, text=label).grid(row=i, column=0, padx=5, pady=5, sticky='e')
            entry = ttk.Entry(dialog)
            entry.insert(0, employee[key])
            entry.grid(row=i, column=1, padx=5, pady=5, sticky='we')
            entries[key] = entry
            
        ttk.Label(dialog, text="Domain:").grid(row=2, column=0, padx=5, pady=5, sticky='e')
        domain_var = StringVar(dialog)
        domain_combo = ttk.Combobox(dialog, textvariable=domain_var, 
                                   values=DOMAIN_OPTIONS, state="readonly")
        domain_combo.grid(row=2, column=1, padx=5, pady=5, sticky='we')
        domain_combo.set(employee['domain'])
            
        def save():
            employee['name'] = entries['name'].get()
            employee['manager'] = entries['manager'].get()
            employee['domain'] = domain_var.get()
            self.save_data()
            self.update_employees_tab()
            self.update_availability_tab()
            self.update_allocation_tab()
            self.update_output1_tab()
            self.update_output2_tab()
            dialog.destroy()
            self.status_var.set(f'Updated employee: {employee["name"]}')
            
        ttk.Button(dialog, text="Save", command=save).grid(row=3, column=1, sticky='e', padx=5, pady=10)
        
    def remove_employee(self):
        selected = self.emp_tree.selection()
        if not selected:
            return
            
        item = selected[0]
        emp_id = self.emp_tree.item(item, 'values')[0]
        emp_name = self.emp_tree.item(item, 'values')[1]
        
        self.data['employees'] = [emp for emp in self.data['employees'] if emp['id'] != emp_id]
        if emp_id in self.data['availability']:
            del self.data['availability'][emp_id]
        self.data['allocation'] = [alloc for alloc in self.data['allocation'] if alloc['employee_id'] != emp_id]
        
        self.save_data()
        self.update_employees_tab()
        self.update_availability_tab()
        self.update_allocation_tab()
        self.update_output1_tab()
        self.update_output2_tab()
        self.status_var.set(f'Removed employee: {emp_name}')
    
    def update_employees_tab(self):
        for item in self.emp_tree.get_children():
            self.emp_tree.delete(item)
            
        for emp in self.data['employees']:
            self.emp_tree.insert('', 'end', values=(
                emp['id'], emp['name'], emp['domain'], emp['manager']
            ))
    
    def setup_availability_tab(self):
        frame = self.tabs["Availability"]
        
        columns = ["employee", "domain"] + [f"month_{i}" for i in range(12)]
        self.avail_tree = DragFillTreeview(
            frame, 
            save_callback=self.save_availability_cell,
            get_rowinfo_callback=self.get_availability_rowinfo,
            columns=columns, 
            show='headings'
        )
        self.avail_tree.heading("employee", text="Employee")
        self.avail_tree.column("employee", width=150, anchor='w')
        self.avail_tree.heading("domain", text="Domain")
        self.avail_tree.column("domain", width=100, anchor='w')
        for i in range(12):
            self.avail_tree.heading(f"month_{i}", text=f"Month {i+1}")
            self.avail_tree.column(f"month_{i}", width=50, minwidth=40, anchor='center')
            self.avail_tree.editable_columns.add(f"#{i+3}") 
        
        self.avail_tree.pack(fill='both', expand=True, padx=10, pady=10)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(btn_frame, text="Add Row", command=self.add_availability_row).pack(side='left')
        ttk.Button(btn_frame, text="Remove Row", command=self.remove_availability_row).pack(side='left', padx=5)
        
        self.update_availability_tab()
        
    def get_availability_rowinfo(self, item, column):
        values = self.avail_tree.item(item, 'values')
        emp_name = values[0]
        employee = next(emp for emp in self.data['employees'] if emp['name'] == emp_name)
        emp_id = employee['id']
        col_index = int(column[1:]) - 1
        month_keys = self.get_month_keys()
        month_key = month_keys[col_index - 2] 
        return (emp_id, month_key)
    
    def save_availability_cell(self, item, column, value, info):
        emp_id, month_key = info
        try:
            value = float(value)
        except ValueError:
            value = 0.0
            
        self.data['availability'].setdefault(emp_id, {})[month_key] = value
        self.save_data()
        
    def add_availability_row(self):
        if not self.data['employees']:
            messagebox.showerror("Error", "Add employees first")
            return
            
        dialog = Toplevel(self)
        dialog.title("Add Availability")
        dialog.geometry("300x150")
        dialog.grab_set()
        
        ttk.Label(dialog, text="Employee:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        emp_var = StringVar(dialog)
        emp_var.set(self.data['employees'][0]['name'])
        emp_names = [emp['name'] for emp in self.data['employees']]
        OptionMenu(dialog, emp_var, *emp_names).grid(row=0, column=1, padx=5, pady=5, sticky='we')
        
        def save():
            employee = next(emp for emp in self.data['employees'] if emp['name'] == emp_var.get())
            emp_id = employee['id']
            month_keys = self.get_month_keys()
            for month in month_keys:
                self.data['availability'].setdefault(emp_id, {})[month] = 0.0
            self.save_data()
            self.update_availability_tab()
            dialog.destroy()
            self.status_var.set(f'Added availability for {emp_var.get()}')
            
        ttk.Button(dialog, text="Save", command=save).grid(row=1, column=1, sticky='e', padx=5, pady=10)
        
    def remove_availability_row(self):
        selected = self.avail_tree.selection()
        if not selected:
            return
            
        item = selected[0]
        emp_name = self.avail_tree.item(item, 'values')[0]
        employee = next(emp for emp in self.data['employees'] if emp['name'] == emp_name)
        
        if employee['id'] in self.data['availability']:
            del self.data['availability'][employee['id']]
            self.save_data()
            self.update_availability_tab()
            self.status_var.set(f'Removed availability for {emp_name}')
        
    def update_availability_tab(self):
        for item in self.avail_tree.get_children():
            self.avail_tree.delete(item)
            
        month_keys = self.get_month_keys()
        for emp in self.data['employees']:
            emp_id = emp['id']
            values = [emp['name'], emp['domain']]
            emp_avail = self.data['availability'].get(emp_id, {})
            for month_key in month_keys:
                values.append(f"{emp_avail.get(month_key, 0):.2f}")
            self.avail_tree.insert('', 'end', values=values, tags=(emp_id,))
            
    def setup_demand_tab(self):
        frame = self.tabs["Demand"]
        
        columns = ["project", "domain", "scaling"] + [f"month_{i}" for i in range(12)]
        self.demand_tree = DragFillTreeview(
            frame, 
            save_callback=self.save_demand_cell,
            get_rowinfo_callback=self.get_demand_rowinfo,
            columns=columns, 
            show='headings'
        )
        self.demand_tree.heading("project", text="Project")
        self.demand_tree.column("project", width=150, anchor='w')
        self.demand_tree.heading("domain", text="Domain")
        self.demand_tree.column("domain", width=100, anchor='w')
        self.demand_tree.heading("scaling", text="Scaling Factor")
        self.demand_tree.column("scaling", width=100, anchor='center')
        for i in range(12):
            self.demand_tree.heading(f"month_{i}", text=f"Month {i+1}")
            self.demand_tree.column(f"month_{i}", width=50, minwidth=40, anchor='center')
            self.demand_tree.editable_columns.add(f"#{i+4}") 
        self.demand_tree.editable_columns.add("#3") 
        
        self.demand_tree.pack(fill='both', expand=True, padx=10, pady=10)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(btn_frame, text="Add Project", command=self.add_project).pack(side='left')
        ttk.Button(btn_frame, text="Remove Project", command=self.remove_project).pack(side='left', padx=5)
        
        self.update_demand_tab()
        
    def get_demand_rowinfo(self, item, column):
        project = self.demand_tree.item(item, 'values')[0]
        col_index = int(column[1:]) - 1
        month_keys = self.get_month_keys()
        if column == "#3":
            return (project, "scaling_factor")
        else:
            month_key = month_keys[col_index - 3] 
            return (project, month_key)
    
    def save_demand_cell(self, item, column, value, info):
        project, field = info
        if field == "scaling_factor":
            try:
                value = float(value)
            except ValueError:
                value = 1.0
            self.data['demand'][project]["scaling_factor"] = value
        else:
            try:
                value = float(value)
            except ValueError:
                value = 0.0
            self.data['demand'][project]["monthly_demand"][field] = value
        self.save_data()
        
    def add_project(self):
        dialog = Toplevel(self)
        dialog.title("Add Project")
        dialog.geometry("300x200")
        dialog.grab_set()
        
        ttk.Label(dialog, text="Project Name:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        project_entry = ttk.Entry(dialog)
        project_entry.grid(row=0, column=1, padx=5, pady=5, sticky='we')
        
        ttk.Label(dialog, text="Domain:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        domain_var = StringVar(dialog)
        domain_combo = ttk.Combobox(dialog, textvariable=domain_var, 
                                   values=DOMAIN_OPTIONS, state="readonly")
        domain_combo.grid(row=1, column=1, padx=5, pady=5, sticky='we')
        domain_combo.current(0)
        
        def save():
            project = project_entry.get()
            if not project:
                messagebox.showerror("Error", "Project name is required")
                return
            self.data['demand'][project] = {
                "domain": domain_var.get(),
                "scaling_factor": 1.0,
                "monthly_demand": {}
            }
            self.save_data()
            self.update_demand_tab()
            self.update_output1_tab()
            dialog.destroy()
            self.status_var.set(f'Added project: {project}')
            
        ttk.Button(dialog, text="Save", command=save).grid(row=2, column=1, sticky='e', padx=5, pady=10)
        
    def remove_project(self):
        selected = self.demand_tree.selection()
        if not selected:
            return
            
        item = selected[0]
        project = self.demand_tree.item(item, 'values')[0]
        
        if project in self.data['demand']:
            del self.data['demand'][project]
            self.status_var.set(f'Removed project: {project}')
            
        self.data['allocation'] = [alloc for alloc in self.data['allocation'] if alloc['project'] != project]
        self.save_data()
        self.update_demand_tab()
        self.update_allocation_tab()
        self.update_output1_tab()
        
    def update_demand_tab(self):
        for item in self.demand_tree.get_children():
            self.demand_tree.delete(item)
            
        month_keys = self.get_month_keys()
        for project, data in self.data['demand'].items():
            values = [
                project,
                data.get('domain', ''),
                f"{data.get('scaling_factor', 1.0):.2f}"
            ]
            for month_key in month_keys:
                values.append(f"{data.get('monthly_demand', {}).get(month_key, 0):.2f}")
            self.demand_tree.insert('', 'end', values=values, tags=(project,))
            
    def setup_allocation_tab(self):
        frame = self.tabs["Allocation"]
        
        columns = ["employee", "domain", "project"] + [f"month_{i}" for i in range(12)]
        self.alloc_tree = DragFillTreeview(
            frame, 
            save_callback=self.save_allocation_cell,
            get_rowinfo_callback=self.get_allocation_rowinfo,
            columns=columns, 
            show='headings'
        )
        self.alloc_tree.heading("employee", text="Employee")
        self.alloc_tree.column("employee", width=150, anchor='w')
        self.alloc_tree.heading("domain", text="Domain")
        self.alloc_tree.column("domain", width=100, anchor='w')
        self.alloc_tree.heading("project", text="Project")
        self.alloc_tree.column("project", width=120, anchor='w')
        for i in range(12):
            self.alloc_tree.heading(f"month_{i}", text=f"Month {i+1}")
            self.alloc_tree.column(f"month_{i}", width=50, minwidth=40, anchor='center')
            self.alloc_tree.editable_columns.add(f"#{i+4}") 
            
        self.alloc_tree.pack(fill='both', expand=True, padx=10, pady=10)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(btn_frame, text="Add Allocation", command=self.add_allocation).pack(side='left')
        ttk.Button(btn_frame, text="Remove Allocation", command=self.remove_allocation).pack(side='left', padx=5)
        
        self.update_allocation_tab()
        
    def get_allocation_rowinfo(self, item, column):
        values = self.alloc_tree.item(item, 'values')
        employee_name = values[0]
        project = values[2]
        employee = next(emp for emp in self.data['employees'] if emp['name'] == employee_name)
        emp_id = employee['id']
        col_index = int(column[1:]) - 1
        month_keys = self.get_month_keys()
        month_key = month_keys[col_index - 3] 
        return (emp_id, project, month_key)
    
    def save_allocation_cell(self, item, column, value, info):
        emp_id, project, month_key = info
        try:
            value = float(value)
        except ValueError:
            value = 0.0
            
        alloc = next(
            (a for a in self.data['allocation'] 
             if a['employee_id'] == emp_id and a['project'] == project),
            None
        )
        
        if not alloc:
            alloc = {
                "employee_id": emp_id,
                "project": project,
                "monthly_allocation": {}
            }
            self.data['allocation'].append(alloc)
            
        alloc['monthly_allocation'][month_key] = value
        self.save_data()
        self.update_output1_tab()
        self.update_output2_tab()
        
    def add_allocation(self):
        if not self.data['employees'] or not self.data['demand']:
            messagebox.showerror("Error", "Add employees and projects first")
            return
            
        dialog = Toplevel(self)
        dialog.title("Add Allocation")
        dialog.geometry("300x150")
        dialog.grab_set()
        
        ttk.Label(dialog, text="Employee:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        emp_var = StringVar(dialog)
        emp_var.set(self.data['employees'][0]['name'])
        emp_names = [emp['name'] for emp in self.data['employees']]
        OptionMenu(dialog, emp_var, *emp_names).grid(row=0, column=1, padx=5, pady=5, sticky='we')
        
        ttk.Label(dialog, text="Project:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        proj_var = StringVar(dialog)
        proj_var.set(list(self.data['demand'].keys())[0])
        OptionMenu(dialog, proj_var, *self.data['demand'].keys()).grid(row=1, column=1, padx=5, pady=5, sticky='we')
        
        def save():
            employee = next(emp for emp in self.data['employees'] if emp['name'] == emp_var.get())
            self.data['allocation'].append({
                "employee_id": employee['id'],
                "project": proj_var.get(),
                "monthly_allocation": {}
            })
            self.save_data()
            self.update_allocation_tab()
            self.update_output1_tab()
            self.update_output2_tab()
            dialog.destroy()
            self.status_var.set(f'Added allocation for {emp_var.get()} on {proj_var.get()}')
            
        ttk.Button(dialog, text="Save", command=save).grid(row=2, column=1, sticky='e', padx=5, pady=10)
        
    def remove_allocation(self):
        selected = self.alloc_tree.selection()
        if not selected:
            return
            
        item = selected[0]
        values = self.alloc_tree.item(item, 'values')
        employee_name = values[0]
        project = values[2]
        
        employee = next(emp for emp in self.data['employees'] if emp['name'] == employee_name)
        self.data['allocation'] = [
            alloc for alloc in self.data['allocation'] 
            if not (alloc['employee_id'] == employee['id'] and alloc['project'] == project)
        ]
        
        self.save_data()
        self.update_allocation_tab()
        self.update_output1_tab()
        self.update_output2_tab()
        self.status_var.set(f'Removed allocation for {employee_name} on {project}')
        
    def update_allocation_tab(self):
        for item in self.alloc_tree.get_children():
            self.alloc_tree.delete(item)
            
        month_keys = self.get_month_keys()
        for alloc in self.data['allocation']:
            employee = next((emp for emp in self.data['employees'] if emp['id'] == alloc['employee_id']), None)
            if not employee:
                continue
            values = [employee['name'], employee['domain'], alloc['project']]
            for month_key in month_keys:
                values.append(f"{alloc.get('monthly_allocation', {}).get(month_key, 0):.2f}")
            self.alloc_tree.insert('', 'end', values=values)
            
    def setup_output_tabs(self):
        self.setup_output1_tab()
        self.setup_output2_tab()
        
    def setup_output1_tab(self):
        frame = self.tabs["Demand-Alloc"]
        columns = ["project", "domain"] + [f"month_{i}" for i in range(12)]
        self.output1_tree = ttk.Treeview(frame, columns=columns, show='headings')
        self.output1_tree.heading("project", text="Project")
        self.output1_tree.column("project", width=150, anchor='w')
        self.output1_tree.heading("domain", text="Domain")
        self.output1_tree.column("domain", width=100, anchor='w')
        for i in range(12):
            self.output1_tree.heading(f"month_{i}", text=f"Month {i+1}")
            self.output1_tree.column(f"month_{i}", width=50, minwidth=40, anchor='center')
        self.output1_tree.pack(fill='both', expand=True, padx=10, pady=10)
        self.update_output1_tab()
        
    def setup_output2_tab(self):
        frame = self.tabs["Alloc-Avail"]
        columns = ["employee", "domain"] + [f"month_{i}" for i in range(12)]
        self.output2_tree = ttk.Treeview(frame, columns=columns, show='headings')
        self.output2_tree.heading("employee", text="Employee")
        self.output2_tree.column("employee", width=150, anchor='w')
        self.output2_tree.heading("domain", text="Domain")
        self.output2_tree.column("domain", width=100, anchor='w')
        for i in range(12):
            self.output2_tree.heading(f"month_{i}", text=f"Month {i+1}")
            self.output2_tree.column(f"month_{i}", width=50, minwidth=40, anchor='center')
        self.output2_tree.pack(fill='both', expand=True, padx=10, pady=10)
        self.update_output2_tab()
        
    def update_output1_tab(self):
        for item in self.output1_tree.get_children():
            self.output1_tree.delete(item)
            
        month_keys = self.get_month_keys()
        thresholds = self.data.get('thresholds', {})
        red_threshold = thresholds.get('output1_red', 1.0)
        blue_threshold = thresholds.get('output1_blue', 0.0)
        
        for project, demand_data in self.data['demand'].items():
            scaling = demand_data.get('scaling_factor', 1.0)
            monthly_demand = demand_data.get('monthly_demand', {})
            
            project_alloc = {month: 0.0 for month in month_keys}
            for alloc in self.data['allocation']:
                if alloc['project'] == project:
                    for month in month_keys:
                        project_alloc[month] += alloc.get('monthly_allocation', {}).get(month, 0)
            
            values = [project, demand_data.get('domain', '')]
            tags = ["normal_cell"] * len(values)
            
            for month in month_keys:
                demand = monthly_demand.get(month, 0)
                diff = scaling * demand - project_alloc[month]
                values.append(f"{diff:.2f}")
                
                diff_val = float(diff)
                if diff_val > red_threshold:
                    tags.append("red_cell")
                elif diff_val < blue_threshold:
                    tags.append("blue_cell")
                else:
                    tags.append("normal_cell")
                    
            item = self.output1_tree.insert('', 'end', values=values)
            for i, tag in enumerate(tags):
                self.output1_tree.tag_configure(tag)
                self.output1_tree.set(item, column=self.output1_tree['columns'][i], value=values[i])
                self.output1_tree.item(item, tags=(tag,))
            
    def update_output2_tab(self):
        for item in self.output2_tree.get_children():
            self.output2_tree.delete(item)
            
        month_keys = self.get_month_keys()
        thresholds = self.data.get('thresholds', {})
        red_threshold = thresholds.get('output2_red', 1.2)
        blue_threshold = thresholds.get('output2_blue', 0.8)
        
        for emp in self.data['employees']:
            emp_id = emp['id']
            availability = self.data['availability'].get(emp_id, {})
            
            emp_alloc = {month: 0.0 for month in month_keys}
            for alloc in self.data['allocation']:
                if alloc['employee_id'] == emp_id:
                    for month in month_keys:
                        emp_alloc[month] += alloc.get('monthly_allocation', {}).get(month, 0)
            
            values = [emp['name'], emp['domain']]
            tags = ["normal_cell"] * len(values)
            
            for month in month_keys:
                avail = availability.get(month, 0)
                diff = avail - emp_alloc[month]
                values.append(f"{diff:.2f}")
                
                diff_val = float(diff)
                if diff_val > red_threshold:
                    tags.append("red_cell")
                elif diff_val < blue_threshold:
                    tags.append("blue_cell")
                else:
                    tags.append("normal_cell")
                    
            item = self.output2_tree.insert('', 'end', values=values)
            for i, tag in enumerate(tags):
                self.output2_tree.tag_configure(tag)
                self.output2_tree.set(item, column=self.output2_tree['columns'][i], value=values[i])
                self.output2_tree.item(item, tags=(tag,))
            
    def open_config(self):
        dialog = Toplevel(self)
        dialog.title("Threshold Configuration")
        dialog.geometry("400x300")
        dialog.grab_set()
        
        thresholds = self.data.get('thresholds', {})
        
        ttk.Label(dialog, text="Demand-Alloc Thresholds", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, columnspan=2, pady=5, sticky='w')
        
        ttk.Label(dialog, text="Red Threshold (>):").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        output1_red_var = tk.DoubleVar(value=thresholds.get('output1_red', 1.0))
        ttk.Entry(dialog, textvariable=output1_red_var).grid(row=1, column=1, padx=5, pady=5, sticky='we')
        
        ttk.Label(dialog, text="Blue Threshold (<):").grid(row=2, column=0, padx=5, pady=5, sticky='e')
        output1_blue_var = tk.DoubleVar(value=thresholds.get('output1_blue', 0.0))
        ttk.Entry(dialog, textvariable=output1_blue_var).grid(row=2, column=1, padx=5, pady=5, sticky='we')
        
        ttk.Label(dialog, text="Alloc-Avail Thresholds", font=('Segoe UI', 10, 'bold')).grid(row=3, column=0, columnspan=2, pady=5, sticky='w')
        
        ttk.Label(dialog, text="Red Threshold (>):").grid(row=4, column=0, padx=5, pady=5, sticky='e')
        output2_red_var = tk.DoubleVar(value=thresholds.get('output2_red', 1.2))
        ttk.Entry(dialog, textvariable=output2_red_var).grid(row=4, column=1, padx=5, pady=5, sticky='we')
        
        ttk.Label(dialog, text="Blue Threshold (<):").grid(row=5, column=0, padx=5, pady=5, sticky='e')
        output2_blue_var = tk.DoubleVar(value=thresholds.get('output2_blue', 0.8))
        ttk.Entry(dialog, textvariable=output2_blue_var).grid(row=5, column=1, padx=5, pady=5, sticky='we')
        
        def save():
            self.data['thresholds'] = {
                'output1_red': output1_red_var.get(),
                'output1_blue': output1_blue_var.get(),
                'output2_red': output2_red_var.get(),
                'output2_blue': output2_blue_var.get()
            }
            self.save_data()
            self.update_output1_tab()
            self.update_output2_tab()
            dialog.destroy()
            self.status_var.set('Thresholds updated and applied')
            
        ttk.Button(dialog, text="Save", command=save).grid(row=6, column=1, sticky='e', padx=5, pady=10)
        
    def update_all_tabs(self):
        self.update_employees_tab()
        self.update_availability_tab()
        self.update_demand_tab()
        self.update_allocation_tab()
        self.update_output1_tab()
        self.update_output2_tab()

if __name__ == "__main__":
    app = StaffingTrackerApp()
    app.mainloop()
