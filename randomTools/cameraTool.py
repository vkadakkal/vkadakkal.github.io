import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.filedialog import asksaveasfilename
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tksheet import Sheet
import sys
import csv

def parse_baselines(baseline_str):
    baselines = []
    for val in baseline_str.split(','):
        val = val.strip()
        if val:
            try:
                n = float(val)
                if n <= 0:
                    raise ValueError
                baselines.append(n)
            except Exception:
                raise ValueError(f"Invalid baseline: '{val.strip()}'")
    if not baselines:
        raise ValueError("Enter one or more positive baseline(s).")
    return baselines

def calculate_camera_params(baseline_in, focal_length_mm, pixel_width, pixel_height,
                            fpa_width_m, fpa_height_m, target_size_m):
    focal_length_m = focal_length_mm / 1000.0
    fov_w_rad = 2 * np.arctan(fpa_width_m / (2 * focal_length_m))
    fov_h_rad = 2 * np.arctan(fpa_height_m / (2 * focal_length_m))
    fov_w_deg = np.degrees(fov_w_rad)
    fov_h_deg = np.degrees(fov_h_rad)
    pixel_size_m = fpa_width_m / pixel_width
    ifov_rad = 2 * np.arctan(pixel_size_m / (2 * focal_length_m))
    ifov_deg = np.degrees(ifov_rad)
    ifov_urad = ifov_rad * 1e6

    def range_at_fill(pct):
        fill_angle = min(fov_w_rad, fov_h_rad) * (pct / 100)
        return target_size_m / (2 * np.tan(fill_angle / 2))

    return {
        "Baseline (in)": baseline_in,
        "Focal Length (mm)": focal_length_mm,
        "W FOV (deg)": fov_w_deg,
        "H FOV (deg)": fov_h_deg,
        "iFOV (deg/pixel)": ifov_deg,
        "iFOV (urad/pixel)": ifov_urad,
        "Range (90% fill, m)": range_at_fill(90),
        "Range (95% fill, m)": range_at_fill(95),
        "Range (100% fill, m)": range_at_fill(100),
        "fov_w_rad": fov_w_rad,
        "fov_h_rad": fov_h_rad,
        "pixel_width": pixel_width,
        "pixel_height": pixel_height,
        "fpa_width_m": fpa_width_m,
        "fpa_height_m": fpa_height_m,
        "focal_length_m": focal_length_m,
        "target_size_m": target_size_m
    }

def calculate_overlap_vs_range(baseline_in, params, range_min, range_max, scale):
    baseline_m = baseline_in * 0.0254
    focal_length_m, fov_w_rad, fov_h_rad = params["focal_length_m"], params["fov_w_rad"], params["fov_h_rad"]
    w, h = params["pixel_width"], params["pixel_height"]
    fpa_w = params["fpa_width_m"]
    tgt = params["target_size_m"]

    ranges = (np.logspace if scale == "Logarithmic" else np.linspace)(
        np.log10(range_min) if scale == "Logarithmic" else range_min,
        np.log10(range_max) if scale == "Logarithmic" else range_max,
        200
    )
    if scale == "Logarithmic":
        ranges = 10 ** ranges

    angular_size = 2 * np.arctan(tgt / (2 * ranges))
    proj_w = angular_size / (fov_w_rad / w)
    proj_h = angular_size / (fov_h_rad / h)
    proj = np.maximum(np.minimum(proj_w, proj_h), 1e-8)
    disparity = (baseline_m * focal_length_m) / (ranges * fpa_w / w)
    overlap = np.clip((proj - disparity) / proj, 0, 1)
    return ranges, overlap * 100

def calculate_and_plot():
    try:
        baseline_list = parse_baselines(entry_baseline.get())
        focal_len = float(entry_focal.get())
        w, h = int(entry_pixel_width.get()), int(entry_pixel_height.get())
        fpa_w, fpa_h = float(entry_fpa_width.get()), float(entry_fpa_height.get())
        tgt_size = float(entry_target_size.get())
        rng_min, rng_max = float(entry_range_min.get()), float(entry_range_max.get())
        scale = range_scale_var.get()

        if rng_max <= rng_min:
            raise ValueError("Max range must be greater than min.")

        result_dicts = []
        curves = []

        for baseline in baseline_list:
            params = calculate_camera_params(baseline, focal_len, w, h, fpa_w, fpa_h, tgt_size)
            result_dicts.append(params)
            xvals, yvals = calculate_overlap_vs_range(baseline, params, rng_min, rng_max, scale)
            curves.append((baseline, xvals, yvals, params["Range (100% fill, m)"]))

        # Plotting
        for widget in plot_frame.winfo_children():
            widget.destroy()

        fig, ax = plt.subplots(figsize=(7, 4), dpi=100)
        root.last_figure = fig
        colors = plt.cm.viridis(np.linspace(0, 1, len(curves)))

        for i, (baseline, xvals, yvals, xfov) in enumerate(curves):
            ax.plot(xvals, yvals, label=f'{baseline}"', color=colors[i])
            ax.axvline(xfov, ls='--', color=colors[i], lw=1, alpha=0.6)

        ax.set_xlabel("Range to Target (m)")
        ax.set_ylabel("Percent Overlap")
        ax.set_title("Overlap vs Range")
        if scale == "Logarithmic":
            ax.set_xscale("log")
        ax.grid(True)
        ax.legend()
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Table Output
        for widget in table_frame.winfo_children():
            widget.destroy()

        rows = [
            "Baseline (in)",
            "Focal Length (mm)",
            "W FOV (deg)",
            "H FOV (deg)",
            "iFOV (deg/pixel)",
            "iFOV (urad/pixel)",
            "Range (90% fill, m)",
            "Range (95% fill, m)",
            "Range (100% fill, m)"
        ]
        headers = [f'{d["Baseline (in)"]}"' for d in result_dicts]
        data = []
        for row in rows:
            data.append([f"{params[row]:.6g}" if "iFOV" in row else f"{params[row]:.2f}" for params in result_dicts])
        data_rows = [[rows[i]] + row for i, row in enumerate(data)]

        sheet = Sheet(table_frame, headers=["Parameter"] + headers, data=data_rows)
        sheet.enable_bindings((
            "single_select", "row_select", "column_select", "column_width_resize",
            "arrowkeys", "right_click_popup_menu", "rc_select", "copy", "cut", "paste", "delete", "edit_cell"
        ))
        sheet.grid(row=0, column=0, sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        root.last_table_data = data_rows
        root.last_table_headers = headers

    except Exception as e:
        messagebox.showerror("Error", f"Calculation failed:\n{e}")

def save_svg():
    if not hasattr(root, "last_figure") or root.last_figure is None:
        messagebox.showerror("No Figure", "Please generate a plot first.")
        return
    path = asksaveasfilename(defaultextension=".svg", filetypes=[("SVG files", "*.svg")])
    if path:
        root.last_figure.savefig(path, format='svg')
        messagebox.showinfo("Saved", f"SVG saved to:\n{path}")

def export_table_to_csv():
    if not hasattr(root, "last_table_data"):
        messagebox.showerror("No Data", "No table data to save.")
        return
    path = asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
    if path:
        try:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Parameter"] + root.last_table_headers)
                for row in root.last_table_data:
                    writer.writerow(row)
            messagebox.showinfo("Saved", f"Table saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"CSV export failed:\n{e}")

# ------- TK GUI Setup -------
root = tk.Tk()
root.title("Stereo Camera Overlap Tool")
root.last_figure = None

mainframe = ttk.Frame(root, padding=10)
mainframe.grid(sticky="nsew")
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

input_frame = ttk.Frame(mainframe)
input_frame.grid(row=0, column=0, sticky="n")

plot_frame = ttk.Frame(mainframe)
plot_frame.grid(row=0, column=1, sticky="nsew")
mainframe.columnconfigure(1, weight=1)

table_frame = ttk.Frame(mainframe)
table_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")

param_labels = [
    ("Camera baseline (in, comma separated):", 'entry_baseline'),
    ("Focal length (mm):", 'entry_focal'),
    ("Pixel width:", 'entry_pixel_width'),
    ("Pixel height:", 'entry_pixel_height'),
    ("FPA width (m):", 'entry_fpa_width'),
    ("FPA height (m):", 'entry_fpa_height'),
    ("Target size (m):", 'entry_target_size'),
    ("Range min (m):", 'entry_range_min'),
    ("Range max (m):", 'entry_range_max')
]

entries = {}
for i, (label, varname) in enumerate(param_labels):
    ttk.Label(input_frame, text=label).grid(column=0, row=i, sticky="w")
    ent = ttk.Entry(input_frame, width=20)
    ent.grid(column=1, row=i, padx=4, pady=2)
    entries[varname] = ent

entry_baseline = entries['entry_baseline']
entry_focal = entries['entry_focal']
entry_pixel_width = entries['entry_pixel_width']
entry_pixel_height = entries['entry_pixel_height']
entry_fpa_width = entries['entry_fpa_width']
entry_fpa_height = entries['entry_fpa_height']
entry_target_size = entries['entry_target_size']
entry_range_min = entries['entry_range_min']
entry_range_max = entries['entry_range_max']

# Range scale option
ttk.Label(input_frame, text="Range scale:").grid(column=0, row=len(param_labels), sticky="w", pady=(6, 0))
range_scale_var = tk.StringVar(value="Linear")
ttk.Combobox(input_frame, textvariable=range_scale_var,
             values=["Linear", "Logarithmic"], state="readonly", width=18).grid(column=1, row=len(param_labels))

# Buttons
ttk.Button(input_frame, text="Calculate & Plot", command=calculate_and_plot)\
    .grid(column=0, row=len(param_labels)+1, columnspan=2, pady=6)
ttk.Button(input_frame, text="Export Plot as SVG", command=save_svg)\
    .grid(column=0, row=len(param_labels)+2, columnspan=2, pady=2)
ttk.Button(input_frame, text="Export Table to CSV", command=export_table_to_csv)\
    .grid(column=0, row=len(param_labels)+3, columnspan=2, pady=2)

def on_closing():
    root.quit()
    root.destroy()
    sys.exit(0)

root.protocol("WM_DELETE_WINDOW", on_closing)

# Set defaults
entry_baseline.insert(0, "8,12,16")
entry_focal.insert(0, "35")
entry_pixel_width.insert(0, "1920")
entry_pixel_height.insert(0, "1200")
entry_fpa_width.insert(0, "0.036")
entry_fpa_height.insert(0, "0.024")
entry_target_size.insert(0, "1.0")
entry_range_min.insert(0, "10")
entry_range_max.insert(0, "1000")

root.mainloop()
