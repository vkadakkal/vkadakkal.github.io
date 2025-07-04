import sys
import os
import json
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QDialog, QLabel, QDoubleSpinBox, QHeaderView, QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt

try:
    import qdarkstyle
except ImportError:
    qdarkstyle = None

MONTH_FORMAT = "%m/%y"
MONTH_JSON_FORMAT = "%Y-%m"
DOMAINS = ["Analysis", "HW", "MPG", "Functional"]

def get_next_months(start_month, count):
    months = []
    dt = datetime.strptime(start_month, MONTH_JSON_FORMAT)
    for i in range(count):
        months.append((dt + timedelta(days=31 * i)).replace(day=1))
    unique_months = []
    seen = set()
    for m in months:
        key = m.strftime(MONTH_JSON_FORMAT)
        if key not in seen:
            unique_months.append(m)
            seen.add(key)
    return unique_months[:count]

def format_month(dt):
    return dt.strftime(MONTH_FORMAT)

def json_month(dt):
    return dt.strftime(MONTH_JSON_FORMAT)

def get_current_month():
    now = datetime.now()
    return now.replace(day=1).strftime(MONTH_JSON_FORMAT)

class StaffingData:
    def __init__(self, filename="staffing_data.json"):
        self.filename = filename
        self.load()

    def load(self):
        if not os.path.exists(self.filename):
            self.data = {
                "employees": [],
                "demand": {},
                "allocation": [],
                "availability": {},
                "thresholds": {
                    "output1_red": 1.0,
                    "output1_blue": 0.0,
                    "output2_red": 1.2,
                    "output2_blue": 0.8
                }
            }
            self.save()
        else:
            with open(self.filename, "r") as f:
                self.data = json.load(f)
        for key in ["employees", "demand", "allocation", "availability", "thresholds"]:
            if key not in self.data:
                if key == "thresholds":
                    self.data[key] = {
                        "output1_red": 1.0,
                        "output1_blue": 0.0,
                        "output2_red": 1.2,
                        "output2_blue": 0.8
                    }
                else:
                    self.data[key] = {}
        self.ensure_availability()

    def ensure_availability(self):
        if "availability" not in self.data:
            self.data["availability"] = {}
        for emp in self.data["employees"]:
            if emp["id"] not in self.data["availability"]:
                self.data["availability"][emp["id"]] = {}

    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.data, f, indent=2)

class DragFillTableWidget(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drag_start_cell = None
        self._drag_value = None
        self._drag_orientation = None

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            idx = self.indexAt(event.pos())
            if idx.isValid():
                self._drag_start_cell = (idx.row(), idx.column())
                item = self.item(idx.row(), idx.column())
                self._drag_value = item.text() if item else ""
                self._drag_orientation = None

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self._drag_start_cell:
            idx = self.indexAt(event.pos())
            if idx.isValid():
                r0, c0 = self._drag_start_cell
                r1, c1 = idx.row(), idx.column()
                if abs(r1 - r0) > abs(c1 - c0):
                    self._drag_orientation = "vertical"
                else:
                    self._drag_orientation = "horizontal"

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self._drag_start_cell and self._drag_orientation:
            r0, c0 = self._drag_start_cell
            idx = self.indexAt(event.pos())
            if idx.isValid():
                r1, c1 = idx.row(), idx.column()
                if self._drag_orientation == "horizontal":
                    row = r0
                    cmin, cmax = sorted([c0, c1])
                    for col in range(cmin, cmax + 1):
                        item = self.item(row, col)
                        if item and (item.flags() & Qt.ItemFlag.ItemIsEditable):
                            item.setText(self._drag_value)
                else:
                    col = c0
                    rmin, rmax = sorted([r0, r1])
                    for row in range(rmin, rmax + 1):
                        item = self.item(row, col)
                        if item and (item.flags() & Qt.ItemFlag.ItemIsEditable):
                            item.setText(self._drag_value)
        self._drag_start_cell = None
        self._drag_value = None
        self._drag_orientation = None

class ThresholdConfigDialog(QDialog):
    def __init__(self, thresholds, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Thresholds")
        self.thresholds = thresholds.copy()
        layout = QVBoxLayout()
        self.spins = {}
        for key, val in thresholds.items():
            row = QHBoxLayout()
            label = QLabel(key)
            spin = QDoubleSpinBox()
            spin.setDecimals(2)
            spin.setRange(-100, 100)
            spin.setValue(val)
            row.addWidget(label)
            row.addWidget(spin)
            layout.addLayout(row)
            self.spins[key] = spin
        btns = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        self.setLayout(layout)

    def get_thresholds(self):
        return {k: self.spins[k].value() for k in self.spins}

class EmployeeTab(QWidget):
    def __init__(self, staffing_data, parent=None):
        super().__init__(parent)
        self.staffing_data = staffing_data
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Domain", "Manager"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.hideColumn(0)
        self.load_data()
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        btns = QHBoxLayout()
        add_btn = QPushButton("Add")
        edit_btn = QPushButton("Edit")
        remove_btn = QPushButton("Remove")
        save_btn = QPushButton("Save")
        add_btn.clicked.connect(self.add_employee)
        edit_btn.clicked.connect(self.edit_employee)
        remove_btn.clicked.connect(self.remove_employee)
        save_btn.clicked.connect(self.save)
        btns.addWidget(add_btn)
        btns.addWidget(edit_btn)
        btns.addWidget(remove_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)
        self.setLayout(layout)

    def load_data(self):
        self.table.setRowCount(0)
        for emp in self.staffing_data.data["employees"]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(emp["id"]))
            self.table.setItem(row, 1, QTableWidgetItem(emp["name"]))
            domain_item = QTableWidgetItem(emp["domain"])
            self.table.setItem(row, 2, domain_item)
            self.table.setItem(row, 3, QTableWidgetItem(emp["manager"]))

    def add_employee(self):
        dialog = EmployeeEditDialog(None, self)
        if dialog.exec():
            emp = dialog.get_employee()
            emp["id"] = str(max([int(e["id"]) for e in self.staffing_data.data["employees"]] + [0]) + 1)
            self.staffing_data.data["employees"].append(emp)
            self.staffing_data.ensure_availability()
            self.load_data()

    def edit_employee(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Edit Employee", "Select an employee to edit.")
            return
        emp_id = self.table.item(row, 0).text()
        emp = next((e for e in self.staffing_data.data["employees"] if e["id"] == emp_id), None)
        if not emp:
            return
        dialog = EmployeeEditDialog(emp.copy(), self)
        if dialog.exec():
            new_emp = dialog.get_employee()
            emp.update(new_emp)
            self.load_data()

    def remove_employee(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Remove Employee", "Select an employee to remove.")
            return
        emp_id = self.table.item(row, 0).text()
        self.staffing_data.data["employees"] = [e for e in self.staffing_data.data["employees"] if e["id"] != emp_id]
        if emp_id in self.staffing_data.data["availability"]:
            del self.staffing_data.data["availability"][emp_id]
        self.staffing_data.data["allocation"] = [a for a in self.staffing_data.data["allocation"] if a["employee_id"] != emp_id]
        self.load_data()

    def save(self):
        self.staffing_data.save()
        QMessageBox.information(self, "Save", "Employee data saved.")

class EmployeeEditDialog(QDialog):
    def __init__(self, emp, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Employee" if emp else "Add Employee")
        layout = QVBoxLayout()
        self.name_edit = QLineEdit()
        self.domain_combo = QComboBox()
        self.domain_combo.addItems(DOMAINS)
        self.manager_edit = QLineEdit()
        if emp:
            self.name_edit.setText(emp["name"])
            idx = self.domain_combo.findText(emp["domain"])
            if idx >= 0:
                self.domain_combo.setCurrentIndex(idx)
            self.manager_edit.setText(emp["manager"])
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Domain:"))
        layout.addWidget(self.domain_combo)
        layout.addWidget(QLabel("Manager:"))
        layout.addWidget(self.manager_edit)
        btns = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        self.setLayout(layout)

    def get_employee(self):
        return {
            "name": self.name_edit.text(),
            "domain": self.domain_combo.currentText(),
            "manager": self.manager_edit.text()
        }

class AvailabilityTab(QWidget):
    def __init__(self, staffing_data, months, set_months_callback, parent=None):
        super().__init__(parent)
        self.staffing_data = staffing_data
        self.months = months
        self.set_months_callback = set_months_callback

        self.table = DragFillTableWidget(0, len(self.months) + 1)
        headers = ["Employee"] + [format_month(m) for m in self.months]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked |
            QTableWidget.EditTrigger.SelectedClicked |
            QTableWidget.EditTrigger.EditKeyPressed
        )
        for i in range(1, len(headers)):
            self.table.setColumnWidth(i, 50)

        layout = QVBoxLayout()
        layout.addWidget(self.table)

        btns = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.edit_btn = QPushButton("Edit")
        self.remove_btn = QPushButton("Remove")
        self.save_btn = QPushButton("Save")
        self.prev_btn = QPushButton("<<")
        self.next_btn = QPushButton(">>")

        self.add_btn.clicked.connect(self.add_availability)
        self.edit_btn.clicked.connect(self.edit_availability)
        self.remove_btn.clicked.connect(self.remove_availability)
        self.save_btn.clicked.connect(self.save)
        self.prev_btn.clicked.connect(lambda: self.set_months_callback(-1))
        self.next_btn.clicked.connect(lambda: self.set_months_callback(1))

        btns.addWidget(self.add_btn)
        btns.addWidget(self.edit_btn)
        btns.addWidget(self.remove_btn)
        btns.addWidget(self.prev_btn)
        btns.addWidget(self.next_btn)
        btns.addWidget(self.save_btn)

        layout.addLayout(btns)
        self.setLayout(layout)

        self.load_data()

    def load_data(self):
        employees = self.staffing_data.data["employees"]
        availability = self.staffing_data.data.get("availability", {})

        self.table.setRowCount(0)
        for emp in employees:
            emp_id = emp["id"]
            row = self.table.rowCount()
            self.table.insertRow(row)

            emp_combo = QComboBox()
            emp_names = [e["name"] for e in self.staffing_data.data["employees"]]
            emp_combo.addItems(emp_names)
            emp_combo.setCurrentText(emp["name"])
            emp_combo.setEnabled(True)
            self.table.setCellWidget(row, 0, emp_combo)

            emp_avail = availability.get(emp_id, {})
            for c, m in enumerate(self.months):
                mkey = json_month(m)
                val = emp_avail.get(mkey, 1.0)
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, c + 1, item)

    def add_availability(self):
        employees = self.staffing_data.data["employees"]
        if not employees:
            QMessageBox.warning(self, "Add Availability", "No employees available. Please add employees first.")
            return

        row = self.table.rowCount()
        self.table.insertRow(row)

        emp_combo = QComboBox()
        emp_names = [e["name"] for e in self.staffing_data.data["employees"]]
        emp_combo.addItems(emp_names)
        emp_combo.setEnabled(True)
        self.table.setCellWidget(row, 0, emp_combo)

        for c in range(len(self.months)):
            item = QTableWidgetItem("1.0")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, c + 1, item)

        self.table.selectRow(row)

    def edit_availability(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Edit Availability", "Select a row to edit.")
            return

        emp_combo = self.table.cellWidget(row, 0)
        if emp_combo:
            emp_combo.setEnabled(True)

        for c in range(1, self.table.columnCount()):
            item = self.table.item(row, c)
            if item:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)

    def remove_availability(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Remove Availability", "Select a row to remove.")
            return

        emp_combo = self.table.cellWidget(row, 0)
        if emp_combo:
            emp_name = emp_combo.currentText()
            emp = next((e for e in self.staffing_data.data["employees"] if e["name"] == emp_name), None)
            if emp and emp["id"] in self.staffing_data.data.get("availability", {}):
                del self.staffing_data.data["availability"][emp["id"]]

        self.table.removeRow(row)

    def save(self):
        employees = self.staffing_data.data["employees"]
        emp_name_to_id = {e["name"]: e["id"] for e in employees}
        availability = {}

        for r in range(self.table.rowCount()):
            emp_combo = self.table.cellWidget(r, 0)
            if not emp_combo:
                continue
            emp_name = emp_combo.currentText()
            emp_id = emp_name_to_id.get(emp_name)
            if not emp_id:
                continue

            monthly_avail = {}
            for c, m in enumerate(self.months):
                item = self.table.item(r, c + 1)
                try:
                    val = float(item.text())
                except Exception:
                    val = 1.0
                monthly_avail[json_month(m)] = val

            availability[emp_id] = monthly_avail

        self.staffing_data.data["availability"] = availability
        self.staffing_data.save()
        QMessageBox.information(self, "Save", "Availability data saved.")

    def update_months(self, months):
        self.months = months
        headers = ["Employee"] + [format_month(m) for m in months]
        self.table.setColumnCount(len(months) + 1)
        self.table.setHorizontalHeaderLabels(headers)
        self.load_data()

# --- DemandTab with Domain column ---
class DemandTab(QWidget):
    def __init__(self, staffing_data, months, set_months_callback, parent=None):
        super().__init__(parent)
        self.staffing_data = staffing_data
        self.months = months
        self.set_months_callback = set_months_callback
        self.table = DragFillTableWidget(0, len(self.months) + 3)  # +3: Project, Domain, Scaling
        headers = ["Project", "Domain", "Scaling"] + [format_month(m) for m in self.months]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked |
            QTableWidget.EditTrigger.SelectedClicked |
            QTableWidget.EditTrigger.EditKeyPressed
        )
        for i in range(3, len(headers)):
            self.table.setColumnWidth(i, 50)
        self.load_data()
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        btns = QHBoxLayout()
        add_btn = QPushButton("Add")
        edit_btn = QPushButton("Edit")
        remove_btn = QPushButton("Remove")
        save_btn = QPushButton("Save")
        prev_btn = QPushButton("<<")
        next_btn = QPushButton(">>")
        add_btn.clicked.connect(self.add_entry)
        edit_btn.clicked.connect(self.edit_entry)
        remove_btn.clicked.connect(self.remove_entry)
        save_btn.clicked.connect(self.save)
        prev_btn.clicked.connect(lambda: self.set_months_callback(-1))
        next_btn.clicked.connect(lambda: self.set_months_callback(1))
        btns.addWidget(add_btn)
        btns.addWidget(edit_btn)
        btns.addWidget(remove_btn)
        btns.addWidget(prev_btn)
        btns.addWidget(next_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)
        self.setLayout(layout)

    def load_data(self):
        projects = list(self.staffing_data.data["demand"].keys())
        self.table.setRowCount(len(projects))
        for r, proj in enumerate(projects):
            proj_combo = QComboBox()
            proj_combo.addItems(list(self.staffing_data.data["demand"].keys()))
            proj_combo.setCurrentText(proj)
            proj_combo.setEnabled(True)
            self.table.setCellWidget(r, 0, proj_combo)
            d = self.staffing_data.data["demand"][proj]
            # Domain
            domain_combo = QComboBox()
            domain_combo.addItems(DOMAINS)
            domain_combo.setCurrentText(d.get("domain", DOMAINS[0]))
            self.table.setCellWidget(r, 1, domain_combo)
            # Scaling
            scaling = d.get("scaling_factor", 1.0)
            scaling_item = QTableWidgetItem(str(scaling))
            scaling_item.setFlags(scaling_item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 2, scaling_item)
            monthly = d.get("monthly_demand", {})
            for c, m in enumerate(self.months):
                mkey = json_month(m)
                val = monthly.get(mkey, 0.0)
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c + 3, item)

    def add_entry(self):
        projects = list(self.staffing_data.data["demand"].keys())
        row = self.table.rowCount()
        self.table.insertRow(row)
        proj_combo = QComboBox()
        proj_combo.addItems(projects)
        proj_combo.setEditable(True)
        self.table.setCellWidget(row, 0, proj_combo)
        domain_combo = QComboBox()
        domain_combo.addItems(DOMAINS)
        self.table.setCellWidget(row, 1, domain_combo)
        scaling_item = QTableWidgetItem("1.0")
        scaling_item.setFlags(scaling_item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 2, scaling_item)
        for c in range(len(self.months)):
            item = QTableWidgetItem("0.0")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, c + 3, item)
        self.table.selectRow(row)

    def edit_entry(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Edit Demand", "Select a row to edit.")
            return
        proj_combo = self.table.cellWidget(row, 0)
        if proj_combo:
            proj_combo.setEnabled(True)
        domain_combo = self.table.cellWidget(row, 1)
        if domain_combo:
            domain_combo.setEnabled(True)
        scaling_item = self.table.item(row, 2)
        if scaling_item:
            scaling_item.setFlags(scaling_item.flags() | Qt.ItemFlag.ItemIsEditable)
        for c in range(3, self.table.columnCount()):
            item = self.table.item(row, c)
            if item:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)

    def remove_entry(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Remove Demand", "Select a row to remove.")
            return
        proj_combo = self.table.cellWidget(row, 0)
        if proj_combo:
            proj = proj_combo.currentText()
            if proj in self.staffing_data.data["demand"]:
                del self.staffing_data.data["demand"][proj]
        self.table.removeRow(row)

    def save(self):
        new_demand = {}
        for r in range(self.table.rowCount()):
            proj_combo = self.table.cellWidget(r, 0)
            domain_combo = self.table.cellWidget(r, 1)
            if not proj_combo or not domain_combo:
                continue
            proj = proj_combo.currentText()
            domain = domain_combo.currentText()
            try:
                scaling = float(self.table.item(r, 2).text())
            except Exception:
                scaling = 1.0
            monthly = {}
            for c, m in enumerate(self.months):
                try:
                    val = float(self.table.item(r, c + 3).text())
                except Exception:
                    val = 0.0
                monthly[json_month(m)] = val
            new_demand[proj] = {
                "domain": domain,
                "scaling_factor": scaling,
                "monthly_demand": monthly
            }
        self.staffing_data.data["demand"] = new_demand
        self.staffing_data.save()
        QMessageBox.information(self, "Save", "Demand data saved.")

    def update_months(self, months):
        self.months = months
        headers = ["Project", "Domain", "Scaling"] + [format_month(m) for m in months]
        self.table.setColumnCount(len(months) + 3)
        self.table.setHorizontalHeaderLabels(headers)
        self.load_data()

    def refresh_project_dropdowns(self):
        projects = list(self.staffing_data.data["demand"].keys())
        for r in range(self.table.rowCount()):
            proj_combo = self.table.cellWidget(r, 0)
            if proj_combo:
                current = proj_combo.currentText()
                proj_combo.clear()
                proj_combo.addItems(projects)
                if current in projects:
                    proj_combo.setCurrentText(current)

# --- AllocationTab with Domain column and Filtering ---
class AllocationTab(QWidget):
    def __init__(self, staffing_data, months, set_months_callback, parent=None):
        super().__init__(parent)
        self.staffing_data = staffing_data
        self.months = months
        self.set_months_callback = set_months_callback

        # Filtering controls
        self.filter_project = QComboBox()
        self.filter_employee = QComboBox()
        self.filter_domain = QComboBox()
        self.filter_project.currentIndexChanged.connect(self.load_data)
        self.filter_employee.currentIndexChanged.connect(self.load_data)
        self.filter_domain.currentIndexChanged.connect(self.load_data)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Project:"))
        filter_layout.addWidget(self.filter_project)
        filter_layout.addWidget(QLabel("Employee:"))
        filter_layout.addWidget(self.filter_employee)
        filter_layout.addWidget(QLabel("Domain:"))
        filter_layout.addWidget(self.filter_domain)
        filter_layout.addStretch()

        self.table = DragFillTableWidget(0, len(self.months) + 3)  # +3: Employee, Project, Domain
        headers = ["Employee", "Project", "Domain"] + [format_month(m) for m in self.months]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked |
            QTableWidget.EditTrigger.SelectedClicked |
            QTableWidget.EditTrigger.EditKeyPressed
        )
        for i in range(3, len(headers)):
            self.table.setColumnWidth(i, 50)
        self.load_data()
        layout = QVBoxLayout()
        layout.addLayout(filter_layout)
        layout.addWidget(self.table)
        btns = QHBoxLayout()
        add_btn = QPushButton("Add")
        remove_btn = QPushButton("Remove")
        save_btn = QPushButton("Save")
        prev_btn = QPushButton("<<")
        next_btn = QPushButton(">>")
        add_btn.clicked.connect(self.add_allocation)
        remove_btn.clicked.connect(self.remove_allocation)
        save_btn.clicked.connect(self.save)
        prev_btn.clicked.connect(lambda: self.set_months_callback(-1))
        next_btn.clicked.connect(lambda: self.set_months_callback(1))
        btns.addWidget(add_btn)
        btns.addWidget(remove_btn)
        btns.addWidget(prev_btn)
        btns.addWidget(next_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)
        self.setLayout(layout)

    def update_filters(self):
        emps = self.staffing_data.data["employees"]
        projects = list(self.staffing_data.data["demand"].keys())
        domains = list(sorted(set(
            d.get("domain", DOMAINS[0]) for d in self.staffing_data.data["demand"].values()
        )))
    
        # Save current selections
        current_proj = self.filter_project.currentText() if self.filter_project.count() else "All"
        current_emp = self.filter_employee.currentText() if self.filter_employee.count() else "All"
        current_domain = self.filter_domain.currentText() if self.filter_domain.count() else "All"
    
        self.filter_project.blockSignals(True)
        self.filter_employee.blockSignals(True)
        self.filter_domain.blockSignals(True)
    
        self.filter_project.clear()
        self.filter_project.addItem("All")
        self.filter_project.addItems(projects)
        # Restore previous selection if possible
        idx = self.filter_project.findText(current_proj)
        self.filter_project.setCurrentIndex(idx if idx != -1 else 0)
    
        self.filter_employee.clear()
        self.filter_employee.addItem("All")
        self.filter_employee.addItems([e["name"] for e in emps])
        idx = self.filter_employee.findText(current_emp)
        self.filter_employee.setCurrentIndex(idx if idx != -1 else 0)
    
        self.filter_domain.clear()
        self.filter_domain.addItem("All")
        self.filter_domain.addItems(domains)
        idx = self.filter_domain.findText(current_domain)
        self.filter_domain.setCurrentIndex(idx if idx != -1 else 0)
    
        self.filter_project.blockSignals(False)
        self.filter_employee.blockSignals(False)
        self.filter_domain.blockSignals(False)
    

    def load_data(self):
        self.update_filters()
        allocations = self.staffing_data.data["allocation"]
        emps = self.staffing_data.data["employees"]
        emp_names = {e["id"]: e["name"] for e in emps}
        projects = list(self.staffing_data.data["demand"].keys())
        project_domains = {proj: self.staffing_data.data["demand"][proj].get("domain", DOMAINS[0]) for proj in projects}
    
        # Get filter selections
        proj_filter = self.filter_project.currentText() if self.filter_project.count() else "All"
        emp_filter = self.filter_employee.currentText() if self.filter_employee.count() else "All"
        domain_filter = self.filter_domain.currentText() if self.filter_domain.count() else "All"
    
        # Filter allocations
        filtered_allocs = []
        for alloc in allocations:
            emp_name = emp_names.get(alloc["employee_id"], "")
            proj = alloc["project"]
            domain = project_domains.get(proj, DOMAINS[0])
            if (proj_filter == "All" or proj == proj_filter) and \
               (emp_filter == "All" or emp_name == emp_filter) and \
               (domain_filter == "All" or domain == domain_filter):
                filtered_allocs.append(alloc)

        self.table.setRowCount(len(filtered_allocs))
        for r, alloc in enumerate(filtered_allocs):
            emp_id = alloc["employee_id"]
            emp_name = emp_names.get(emp_id, "")
            emp_combo = QComboBox()
            emp_combo.addItems([e["name"] for e in emps])
            if emp_name in [e["name"] for e in emps]:
                emp_combo.setCurrentIndex([e["name"] for e in emps].index(emp_name))
            self.table.setCellWidget(r, 0, emp_combo)
            proj_combo = QComboBox()
            proj_combo.addItems(projects)
            if alloc["project"] in projects:
                proj_combo.setCurrentIndex(projects.index(alloc["project"]))
            self.table.setCellWidget(r, 1, proj_combo)
            # Domain column (read-only)
            domain = project_domains.get(alloc["project"], DOMAINS[0])
            domain_item = QTableWidgetItem(domain)
            domain_item.setFlags(domain_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 2, domain_item)
            monthly = alloc.get("monthly_allocation", {})
            for c, m in enumerate(self.months):
                mkey = json_month(m)
                val = monthly.get(mkey, 0.0)
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c + 3, item)

    def add_allocation(self):
        self.table.insertRow(self.table.rowCount())
        emps = self.staffing_data.data["employees"]
        emp_combo = QComboBox()
        emp_combo.addItems([e["name"] for e in emps])
        self.table.setCellWidget(self.table.rowCount() - 1, 0, emp_combo)
        projects = list(self.staffing_data.data["demand"].keys())
        proj_combo = QComboBox()
        proj_combo.addItems(projects)
        self.table.setCellWidget(self.table.rowCount() - 1, 1, proj_combo)
        # Domain
        domain = DOMAINS[0]
        if projects:
            domain = self.staffing_data.data["demand"][projects[0]].get("domain", DOMAINS[0])
        domain_item = QTableWidgetItem(domain)
        domain_item.setFlags(domain_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(self.table.rowCount() - 1, 2, domain_item)
        for c in range(3, self.table.columnCount()):
            item = QTableWidgetItem("0.0")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(self.table.rowCount() - 1, c, item)

    def remove_allocation(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Remove Allocation", "Select an allocation to remove.")
            return
        self.table.removeRow(row)

    def save(self):
        emps = self.staffing_data.data["employees"]
        emp_names = {e["name"]: e["id"] for e in emps}
        projects = list(self.staffing_data.data["demand"].keys())
        allocations = []
        for r in range(self.table.rowCount()):
            emp_combo = self.table.cellWidget(r, 0)
            proj_combo = self.table.cellWidget(r, 1)
            if not emp_combo or not proj_combo:
                continue
            emp_name = emp_combo.currentText()
            proj = proj_combo.currentText()
            emp_id = emp_names.get(emp_name)
            if not emp_id:
                continue
            monthly = {}
            for c, m in enumerate(self.months):
                item = self.table.item(r, c + 3)
                try:
                    val = float(item.text())
                except Exception:
                    val = 0.0
                monthly[json_month(m)] = val
            allocations.append({
                "employee_id": emp_id,
                "project": proj,
                "monthly_allocation": monthly
            })
        self.staffing_data.data["allocation"] = allocations
        self.staffing_data.save()
        QMessageBox.information(self, "Save", "Allocation data saved.")

    def update_months(self, months):
        self.months = months
        headers = ["Employee", "Project", "Domain"] + [format_month(m) for m in months]
        self.table.setColumnCount(len(months) + 3)
        self.table.setHorizontalHeaderLabels(headers)
        self.load_data()

    def refresh_project_dropdowns(self):
        projects = list(self.staffing_data.data["demand"].keys())
        for r in range(self.table.rowCount()):
            proj_combo = self.table.cellWidget(r, 1)
            if proj_combo:
                current = proj_combo.currentText()
                proj_combo.clear()
                proj_combo.addItems(projects)
                if current in projects:
                    proj_combo.setCurrentText(current)

# --- DemandAllocationOutputTab with Domain column ---
class DemandAllocationOutputTab(QWidget):
    def __init__(self, staffing_data, months, set_months_callback, parent=None):
        super().__init__(parent)
        self.staffing_data = staffing_data
        self.months = months
        self.set_months_callback = set_months_callback
        self.projects = list(self.staffing_data.data["demand"].keys())
        self.table = QTableWidget(len(self.projects), len(self.months) + 2)  # +2: Domain, Scaling
        headers = ["Domain", "Scaling"] + [format_month(m) for m in self.months]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setVerticalHeaderLabels(self.projects)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for i in range(2, len(headers)):
            self.table.setColumnWidth(i, 50)
        self.load_data()
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        btns = QHBoxLayout()
        config_btn = QPushButton("Config")
        save_btn = QPushButton("Save")
        prev_btn = QPushButton("<<")
        next_btn = QPushButton(">>")
        config_btn.clicked.connect(self.config)
        save_btn.clicked.connect(self.save)
        prev_btn.clicked.connect(lambda: self.set_months_callback(-1))
        next_btn.clicked.connect(lambda: self.set_months_callback(1))
        btns.addWidget(config_btn)
        btns.addWidget(prev_btn)
        btns.addWidget(next_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)
        self.setLayout(layout)

    def load_data(self):
        self.projects = list(self.staffing_data.data["demand"].keys())
        self.table.setRowCount(len(self.projects))
        self.table.setVerticalHeaderLabels(self.projects)
        allocations = self.staffing_data.data["allocation"]
        thresholds = self.staffing_data.data["thresholds"]
        for r, proj in enumerate(self.projects):
            d = self.staffing_data.data["demand"][proj]
            domain = d.get("domain", DOMAINS[0])
            scaling = d.get("scaling_factor", 1.0)
            domain_item = QTableWidgetItem(domain)
            domain_item.setFlags(domain_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 0, domain_item)
            scaling_item = QTableWidgetItem(str(scaling))
            scaling_item.setFlags(scaling_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 1, scaling_item)
            monthly_demand = d.get("monthly_demand", {})
            alloc_by_month = {json_month(m): 0.0 for m in self.months}
            for alloc in allocations:
                if alloc["project"] == proj:
                    for m in self.months:
                        mkey = json_month(m)
                        alloc_by_month[mkey] += alloc.get("monthly_allocation", {}).get(mkey, 0.0)
            for c, m in enumerate(self.months):
                mkey = json_month(m)
                val = scaling * monthly_demand.get(mkey, 0.0) - alloc_by_month.get(mkey, 0.0)
                item = QTableWidgetItem(f"{val:.2f}")
                if val > thresholds["output1_red"]:
                    item.setBackground(Qt.GlobalColor.red)
                elif val < thresholds["output1_blue"]:
                    item.setBackground(Qt.GlobalColor.blue)
                self.table.setItem(r, c + 2, item)

    def config(self):
        dialog = ThresholdConfigDialog(self.staffing_data.data["thresholds"], self)
        if dialog.exec():
            self.staffing_data.data["thresholds"].update(dialog.get_thresholds())
            self.staffing_data.save()
            self.load_data()

    def save(self):
        self.staffing_data.save()
        QMessageBox.information(self, "Save", "Output data saved.")

    def update_months(self, months):
        self.months = months
        headers = ["Domain", "Scaling"] + [format_month(m) for m in self.months]
        self.table.setColumnCount(len(months) + 2)
        self.table.setHorizontalHeaderLabels(headers)
        self.load_data()

# --- AvailabilityAllocationOutputTab unchanged ---

class AvailabilityAllocationOutputTab(QWidget):
    def __init__(self, staffing_data, months, set_months_callback, parent=None):
        super().__init__(parent)
        self.staffing_data = staffing_data
        self.months = months
        self.set_months_callback = set_months_callback
        self.emps = self.staffing_data.data["employees"]
        self.table = QTableWidget(len(self.emps), len(self.months))
        self.table.setHorizontalHeaderLabels([format_month(m) for m in self.months])
        self.table.setVerticalHeaderLabels([e["name"] for e in self.emps])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for i in range(len(self.months)):
            self.table.setColumnWidth(i, 50)
        self.load_data()
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        btns = QHBoxLayout()
        config_btn = QPushButton("Config")
        save_btn = QPushButton("Save")
        prev_btn = QPushButton("<<")
        next_btn = QPushButton(">>")
        config_btn.clicked.connect(self.config)
        save_btn.clicked.connect(self.save)
        prev_btn.clicked.connect(lambda: self.set_months_callback(-1))
        next_btn.clicked.connect(lambda: self.set_months_callback(1))
        btns.addWidget(config_btn)
        btns.addWidget(prev_btn)
        btns.addWidget(next_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)
        self.setLayout(layout)

    def load_data(self):
        self.emps = self.staffing_data.data["employees"]
        self.table.setRowCount(len(self.emps))
        self.table.setVerticalHeaderLabels([e["name"] for e in self.emps])
        allocations = self.staffing_data.data["allocation"]
        thresholds = self.staffing_data.data["thresholds"]
        avail = self.staffing_data.data["availability"]
        for r, emp in enumerate(self.emps):
            emp_id = emp["id"]
            emp_avail = avail.get(emp_id, {})
            alloc_by_month = {json_month(m): 0.0 for m in self.months}
            for alloc in allocations:
                if alloc["employee_id"] == emp_id:
                    for m in self.months:
                        mkey = json_month(m)
                        alloc_by_month[mkey] += alloc.get("monthly_allocation", {}).get(mkey, 0.0)
            for c, m in enumerate(self.months):
                mkey = json_month(m)
                val = emp_avail.get(mkey, 1.0) - alloc_by_month.get(mkey, 0.0)
                item = QTableWidgetItem(f"{val:.2f}")
                if val > thresholds["output2_red"]:
                    item.setBackground(Qt.GlobalColor.red)
                elif val < thresholds["output2_blue"]:
                    item.setBackground(Qt.GlobalColor.blue)
                self.table.setItem(r, c, item)

    def config(self):
        dialog = ThresholdConfigDialog(self.staffing_data.data["thresholds"], self)
        if dialog.exec():
            self.staffing_data.data["thresholds"].update(dialog.get_thresholds())
            self.staffing_data.save()
            self.load_data()

    def save(self):
        self.staffing_data.save()
        QMessageBox.information(self, "Save", "Output data saved.")

    def update_months(self, months):
        self.months = months
        self.table.setColumnCount(len(months))
        self.table.setHorizontalHeaderLabels([format_month(m) for m in months])
        self.load_data()

# --- ProjectsTab and ProjectEditDialog unchanged ---

class ProjectsTab(QWidget):
    def __init__(self, staffing_data, parent=None):
        super().__init__(parent)
        self.staffing_data = staffing_data
        self.parent_main = None
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Project Name", "Scaling Factor"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.load_data()
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        btns = QHBoxLayout()
        add_btn = QPushButton("Add")
        edit_btn = QPushButton("Edit")
        remove_btn = QPushButton("Remove")
        save_btn = QPushButton("Save")
        add_btn.clicked.connect(self.add_project)
        edit_btn.clicked.connect(self.edit_project)
        remove_btn.clicked.connect(self.remove_project)
        save_btn.clicked.connect(self.save)
        btns.addWidget(add_btn)
        btns.addWidget(edit_btn)
        btns.addWidget(remove_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)
        self.setLayout(layout)

    def set_parent_main(self, parent_main):
        self.parent_main = parent_main

    def load_data(self):
        self.table.setRowCount(0)
        for proj, data in self.staffing_data.data["demand"].items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(proj))
            self.table.setItem(row, 1, QTableWidgetItem(str(data.get("scaling_factor", 1.0))))

    def add_project(self):
        dialog = ProjectEditDialog(None, self)
        if dialog.exec():
            proj, scaling = dialog.get_project()
            if proj in self.staffing_data.data["demand"]:
                QMessageBox.warning(self, "Add Project", "Project already exists.")
                return
            self.staffing_data.data["demand"][proj] = {
                "domain": DOMAINS[0],
                "scaling_factor": scaling,
                "monthly_demand": {}
            }
            self.load_data()
            if self.parent_main:
                self.parent_main.demand_tab.refresh_project_dropdowns()
                self.parent_main.allocation_tab.refresh_project_dropdowns()
                self.parent_main.reload_outputs()

    def edit_project(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Edit Project", "Select a project to edit.")
            return
        proj = self.table.item(row, 0).text()
        data = self.staffing_data.data["demand"][proj]
        dialog = ProjectEditDialog((proj, data.get("scaling_factor", 1.0)), self)
        if dialog.exec():
            new_proj, scaling = dialog.get_project()
            if new_proj != proj and new_proj in self.staffing_data.data["demand"]:
                QMessageBox.warning(self, "Edit Project", "Project name already exists.")
                return
            if new_proj != proj:
                self.staffing_data.data["demand"][new_proj] = self.staffing_data.data["demand"].pop(proj)
                for alloc in self.staffing_data.data["allocation"]:
                    if alloc["project"] == proj:
                        alloc["project"] = new_proj
            self.staffing_data.data["demand"][new_proj]["scaling_factor"] = scaling
            self.load_data()
            if self.parent_main:
                self.parent_main.demand_tab.refresh_project_dropdowns()
                self.parent_main.allocation_tab.refresh_project_dropdowns()
                self.parent_main.reload_outputs()

    def remove_project(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Remove Project", "Select a project to remove.")
            return
        proj = self.table.item(row, 0).text()
        reply = QMessageBox.question(self, "Remove Project", f"Remove project '{proj}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            del self.staffing_data.data["demand"][proj]
            self.staffing_data.data["allocation"] = [a for a in self.staffing_data.data["allocation"] if a["project"] != proj]
            self.load_data()
            if self.parent_main:
                self.parent_main.demand_tab.refresh_project_dropdowns()
                self.parent_main.allocation_tab.refresh_project_dropdowns()
                self.parent_main.reload_outputs()

    def save(self):
        self.staffing_data.save()
        QMessageBox.information(self, "Save", "Project data saved.")

class ProjectEditDialog(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Project" if project else "Add Project")
        layout = QVBoxLayout()
        self.name_edit = QLineEdit()
        self.scaling_spin = QDoubleSpinBox()
        self.scaling_spin.setDecimals(2)
        self.scaling_spin.setRange(0, 100)
        if project:
            self.name_edit.setText(project[0])
            self.scaling_spin.setValue(project[1])
        layout.addWidget(QLabel("Project Name:"))
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Scaling Factor:"))
        layout.addWidget(self.scaling_spin)
        btns = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        self.setLayout(layout)

    def get_project(self):
        return self.name_edit.text(), self.scaling_spin.value()

class StaffingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Staffing Demand vs Availability Tracker")
        self.resize(1200, 700)
        self.staffing_data = StaffingData()
        self.current_month = get_current_month()
        self.month_window = 12
        self.months = get_next_months(self.current_month, self.month_window)
        self.tabs = QTabWidget()
        self.projects_tab = ProjectsTab(self.staffing_data)
        self.employee_tab = EmployeeTab(self.staffing_data)
        self.availability_tab = AvailabilityTab(self.staffing_data, self.months, self.shift_months)
        self.demand_tab = DemandTab(self.staffing_data, self.months, self.shift_months)
        self.allocation_tab = AllocationTab(self.staffing_data, self.months, self.shift_months)
        self.demand_alloc_output_tab = DemandAllocationOutputTab(self.staffing_data, self.months, self.shift_months)
        self.avail_alloc_output_tab = AvailabilityAllocationOutputTab(self.staffing_data, self.months, self.shift_months)
        self.projects_tab.set_parent_main(self)
        self.tabs.addTab(self.projects_tab, "Projects")
        self.tabs.addTab(self.employee_tab, "Employees")
        self.tabs.addTab(self.availability_tab, "Availability")
        self.tabs.addTab(self.demand_tab, "Demand")
        self.tabs.addTab(self.allocation_tab, "Allocation")
        self.tabs.addTab(self.demand_alloc_output_tab, "Out: Demand-Allocation")
        self.tabs.addTab(self.avail_alloc_output_tab, "Out: Availability-Allocation")
        self.setCentralWidget(self.tabs)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # Dynamic output update on cell edit
        self.availability_tab.table.cellChanged.connect(self.reload_outputs)
        self.demand_tab.table.cellChanged.connect(self.reload_outputs)
        self.allocation_tab.table.cellChanged.connect(self.reload_outputs)

    def shift_months(self, delta):
        dt = datetime.strptime(self.current_month, MONTH_JSON_FORMAT)
        month = dt.month + delta
        year = dt.year
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        dt = dt.replace(year=year, month=month)
        self.current_month = dt.strftime(MONTH_JSON_FORMAT)
        self.months = get_next_months(self.current_month, self.month_window)
        self.availability_tab.update_months(self.months)
        self.demand_tab.update_months(self.months)
        self.allocation_tab.update_months(self.months)
        self.demand_alloc_output_tab.update_months(self.months)
        self.avail_alloc_output_tab.update_months(self.months)
        self.reload_outputs()

    def on_tab_changed(self, idx):
        widget = self.tabs.widget(idx)
        if widget == self.demand_tab:
            self.demand_tab.refresh_project_dropdowns()
        elif widget == self.allocation_tab:
            self.allocation_tab.refresh_project_dropdowns()

    def reload_outputs(self):
        self.demand_alloc_output_tab.load_data()
        self.avail_alloc_output_tab.load_data()

def main():
    app = QApplication(sys.argv)
    if qdarkstyle:
        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
    win = StaffingApp()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

