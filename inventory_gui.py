import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from collections import deque
import datetime
import json
import csv
from tkinter.scrolledtext import ScrolledText

class Item:
    def __init__(self, name, category, price=0.0):
        self.name = name
        self.category = category
        self.price = float(price)
        self.quantity = 0
        self.expiry_queue = deque()
        self.date_added = datetime.date.today()

    def add_stock(self, quantity, expiry_date):
        self.quantity += quantity
        self.expiry_queue.append((expiry_date, quantity))
        self.expiry_queue = deque(sorted(self.expiry_queue, key=lambda x: x[0]))

    def remove_expired(self):
        today = datetime.date.today()
        removed = 0
        while self.expiry_queue and self.expiry_queue[0][0] < today:
            _, qty = self.expiry_queue.popleft()
            self.quantity -= qty
            removed += qty
        return removed

    def to_dict(self):
        return {
            'name': self.name,
            'category': self.category,
            'price': self.price,
            'quantity': self.quantity,
            'expiry_dates': [str(exp[0]) for exp in self.expiry_queue],
            'date_added': str(self.date_added)
        }

class InventoryManager:
    def __init__(self):
        self.items = {}
        self.action_stack = []
        self.categories = set()

    def add_item(self, name, category, price=0.0):
        if name not in self.items:
            self.items[name] = Item(name, category, price)
            self.categories.add(category)
            self.action_stack.append(('delete_item', name))
            return True
        return False

    def update_quantity(self, name, quantity, expiry_date):
        if name in self.items:
            try:
                expiry_date = datetime.datetime.strptime(expiry_date, "%Y-%m-%d").date()
                self.items[name].add_stock(int(quantity), expiry_date)
                self.action_stack.append(('update_quantity', name, -int(quantity)))
                return True
            except ValueError:
                return False
        return False

    def remove_expired(self):
        results = []
        for item in self.items.values():
            removed = item.remove_expired()
            if removed:
                results.append(f"{removed} units removed from '{item.name}'")
        return results

    def undo_last_action(self):
        if not self.action_stack:
            return "No actions to undo."
        action = self.action_stack.pop()
        if action[0] == 'delete_item':
            item = self.items[action[1]]
            self.categories.discard(item.category)
            del self.items[action[1]]
            return f"Undid: Deleted item '{action[1]}'"
        elif action[0] == 'update_quantity':
            self.items[action[1]].quantity += action[2]
            return f"Undid: Quantity adjustment for '{action[1]}'"

    def generate_report(self, category_filter=None):
        report = []
        for name, item in sorted(self.items.items()):
            if category_filter and item.category != category_filter:
                continue
            report.append({
                'Name': name,
                'Category': item.category,
                'Quantity': item.quantity,
                'Price': f"₹{item.price:.2f}",
                'Value': f"₹{item.quantity * item.price:.2f}",
                'Expiry Dates': ", ".join(str(exp[0]) for exp in item.expiry_queue)
            })
        return report

    def get_item_details(self, name):
        if name in self.items:
            item = self.items[name]
            return {
                'Name': name,
                'Category': item.category,
                'Quantity': item.quantity,
                'Price': item.price,
                'Total Value': item.quantity * item.price,
                'Expiry Dates': [str(exp[0]) for exp in item.expiry_queue]
            }
        return None

    def export_to_json(self, filename):
        data = {name: item.to_dict() for name, item in self.items.items()}
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

    def import_from_json(self, filename):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            for name, item_data in data.items():
                self.add_item(name, item_data['category'], item_data['price'])
                expiry_dates = [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in item_data['expiry_dates']]
                for date in expiry_dates:
                    self.update_quantity(name, 1, str(date))
            return True
        except Exception as e:
            return False

class InventoryApp:
    def __init__(self, root):
        self.manager = InventoryManager()
        self.root = root
        self.root.title("Inventory Manager Pro")
        self.root.geometry("800x700")
        self.root.minsize(700, 600)
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.create_widgets()
        self.setup_layout()
        self.setup_menu()

    def create_widgets(self):
        # Notebook for multiple tabs
        self.notebook = ttk.Notebook(self.root)
        
        # Main Tab
        self.main_frame = ttk.Frame(self.notebook)
        self.create_main_tab()
        
        # Report Tab
        self.report_frame = ttk.Frame(self.notebook)
        self.create_report_tab()
        
        self.notebook.add(self.main_frame, text="Inventory Management")
        self.notebook.add(self.report_frame, text="Reports & Analytics")
        
        # Output console
        self.console = ScrolledText(self.root, height=10, state='disabled')
        self.console.tag_config('success', foreground='green')
        self.console.tag_config('error', foreground='red')
        self.console.tag_config('warning', foreground='orange')

    def create_main_tab(self):
        # Input Frame
        input_frame = ttk.LabelFrame(self.main_frame, text="Item Details", padding=10)
        
        # Form fields
        fields = [
            ("Item Name", "name_entry"),
            ("Category", "cat_entry"),
            ("Price (₹)", "price_entry"),
            ("Quantity", "qty_entry"),
            ("Expiry Date (YYYY-MM-DD)", "exp_entry")
        ]
        
        self.entries = {}
        for i, (label, var_name) in enumerate(fields):
            ttk.Label(input_frame, text=label).grid(row=i, column=0, sticky='w', padx=5, pady=5)
            entry = ttk.Entry(input_frame)
            entry.grid(row=i, column=1, sticky='ew', padx=5, pady=5)
            self.entries[var_name] = entry
        
        # Auto-complete for categories
        self.cat_var = tk.StringVar()
        self.cat_combobox = ttk.Combobox(input_frame, textvariable=self.cat_var)
        self.entries['cat_entry'] = self.cat_var  # So other parts of the app access the correct value
        self.cat_combobox.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)
        
        self.add_btn = ttk.Button(btn_frame, text="Add Item", command=self.add_item)
        self.add_btn.pack(side=tk.LEFT, padx=5)
        
        self.update_btn = ttk.Button(btn_frame, text="Update Stock", command=self.update_quantity)
        self.update_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(btn_frame, text="Clear", command=self.clear_form)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Action buttons
        action_frame = ttk.Frame(self.main_frame)
        
        self.expired_btn = ttk.Button(action_frame, text="Remove Expired", command=self.remove_expired)
        self.expired_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.undo_btn = ttk.Button(action_frame, text="Undo", command=self.undo_action)
        self.undo_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.search_btn = ttk.Button(action_frame, text="Search Item", command=self.search_item)
        self.search_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Item details display
        self.details_frame = ttk.LabelFrame(self.main_frame, text="Item Details", padding=10)
        self.details_text = ScrolledText(self.details_frame, height=10, state='disabled')
        self.details_text.pack(fill=tk.BOTH, expand=True)
        self.details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def create_report_tab(self):
        # Filter controls
        filter_frame = ttk.Frame(self.report_frame)
        
        ttk.Label(filter_frame, text="Filter by Category:").pack(side=tk.LEFT, padx=5)
        self.category_filter = ttk.Combobox(filter_frame, state='readonly')
        self.category_filter.pack(side=tk.LEFT, padx=5)
        self.category_filter.bind('<<ComboboxSelected>>', self.update_report)
        
        self.refresh_btn = ttk.Button(filter_frame, text="Refresh", command=self.update_report)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        self.export_btn = ttk.Button(filter_frame, text="Export Report", command=self.export_report)
        self.export_btn.pack(side=tk.LEFT, padx=5)
        
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Report Treeview
        self.report_tree = ttk.Treeview(self.report_frame, columns=('Name', 'Category', 'Quantity', 'Price', 'Value', 'Expiry Dates'), show='headings')
        
        # Configure columns
        columns = [
            ('Name', 150),
            ('Category', 100),
            ('Quantity', 80),
            ('Price', 80),
            ('Value', 100),
            ('Expiry Dates', 200)
        ]
        
        for col, width in columns:
            self.report_tree.heading(col, text=col)
            self.report_tree.column(col, width=width, anchor='center')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.report_frame, orient=tk.VERTICAL, command=self.report_tree.yview)
        self.report_tree.configure(yscroll=scrollbar.set)
        self.report_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Summary frame
        summary_frame = ttk.LabelFrame(self.report_frame, text="Inventory Summary", padding=10)
        
        self.summary_vars = {
            'Total Items': tk.StringVar(),
            'Total Quantity': tk.StringVar(),
            'Total Value': tk.StringVar()
        }
        
        for i, (label, var) in enumerate(self.summary_vars.items()):
            ttk.Label(summary_frame, text=label).grid(row=i, column=0, sticky='w', padx=5, pady=2)
            ttk.Label(summary_frame, textvariable=var).grid(row=i, column=1, sticky='e', padx=5, pady=2)
        
        summary_frame.pack(fill=tk.X, padx=10, pady=5)

    def setup_layout(self):
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.console.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)
        
        # Configure grid weights
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.report_frame.grid_rowconfigure(0, weight=1)
        self.report_frame.grid_columnconfigure(0, weight=1)

    def setup_menu(self):
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Import JSON", command=self.import_data)
        file_menu.add_command(label="Export JSON", command=self.export_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)

    def print_output(self, message, msg_type='info'):
        self.console.configure(state='normal')
        self.console.insert(tk.END, message + '\n', msg_type)
        self.console.see(tk.END)
        self.console.configure(state='disabled')

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.update_category_list()

    def update_category_list(self):
        categories = sorted(self.manager.categories)
        self.cat_combobox['values'] = categories
        self.category_filter['values'] = ['All'] + categories

    def add_item(self):
        name = self.entries['name_entry'].get().strip()
        category = self.entries['cat_entry'].get().strip()
        price = self.entries['price_entry'].get().strip()
        
        if not name or not category:
            self.print_output("Name and category are required.", 'error')
            return
            
        try:
            price = float(price) if price else 0.0
            if self.manager.add_item(name, category, price):
                self.print_output(f"Item '{name}' added successfully.", 'success')
                self.update_category_list()
                self.update_report()
            else:
                self.print_output(f"Item '{name}' already exists.", 'warning')
        except ValueError:
            self.print_output("Invalid price value.", 'error')

    def update_quantity(self):
        name = self.entries['name_entry'].get().strip()
        qty = self.entries['qty_entry'].get().strip()
        expiry = self.entries['exp_entry'].get().strip()
        
        if not name or not qty or not expiry:
            self.print_output("Name, quantity and expiry date are required.", 'error')
            return
            
        if name not in self.manager.items:
            self.print_output(f"Item '{name}' not found.", 'error')
            return
            
        try:
            datetime.datetime.strptime(expiry, "%Y-%m-%d")
        except ValueError:
            self.print_output("Invalid date format. Use YYYY-MM-DD.", 'error')
            return
            
        try:
            qty = int(qty)
            if qty <= 0:
                raise ValueError
        except ValueError:
            self.print_output("Quantity must be a positive integer.", 'error')
            return
            
        if self.manager.update_quantity(name, qty, expiry):
            self.print_output(f"Added {qty} units to '{name}' with expiry {expiry}.", 'success')
            self.show_item_details(name)
            self.update_report()
        else:
            self.print_output("Failed to update quantity.", 'error')

    def remove_expired(self):
        results = self.manager.remove_expired()
        if results:
            for r in results:
                self.print_output(r, 'warning')
            self.print_output("Expired items removed.", 'success')
        else:
            self.print_output("No expired items found.", 'info')
        self.update_report()

    def undo_action(self):
        message = self.manager.undo_last_action()
        if message:
            self.print_output(message, 'warning')
            self.update_report()
        else:
            self.print_output("No actions to undo.", 'info')

    def search_item(self):
        name = self.entries['name_entry'].get().strip()
        if not name:
            self.print_output("Please enter an item name to search.", 'error')
            return
            
        self.show_item_details(name)

    def show_item_details(self, name):
        details = self.manager.get_item_details(name)
        self.details_text.configure(state='normal')
        self.details_text.delete(1.0, tk.END)
        
        if details:
            for key, value in details.items():
                if key == 'Expiry Dates':
                    self.details_text.insert(tk.END, f"{key}:\n", 'heading')
                    for date in value:
                        self.details_text.insert(tk.END, f"  - {date}\n")
                else:
                    self.details_text.insert(tk.END, f"{key}: ", 'heading')
                    self.details_text.insert(tk.END, f"{value}\n")
        else:
            self.details_text.insert(tk.END, f"Item '{name}' not found.", 'error')
            
        self.details_text.configure(state='disabled')

    def update_report(self, event=None):
        # Clear existing data
        for row in self.report_tree.get_children():
            self.report_tree.delete(row)
        
        # Get filter
        category = self.category_filter.get()
        category = None if category == 'All' or not category else category
        
        # Generate report
        report = self.manager.generate_report(category)
        
        # Update treeview
        for item in report:
            self.report_tree.insert('', tk.END, values=(
                item['Name'],
                item['Category'],
                item['Quantity'],
                item['Price'],
                item['Value'],
                item['Expiry Dates']
            ))
        
        # Update summary
        total_items = len(report)
        total_qty = sum(int(item['Quantity']) for item in report)
        total_value = sum(float(item['Value'].replace('$', '')) for item in report)
        
        self.summary_vars['Total Items'].set(str(total_items))
        self.summary_vars['Total Quantity'].set(str(total_qty))
        self.summary_vars['Total Value'].set(f"${total_value:.2f}")

    def export_report(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not filename:
            return
            
        category = self.category_filter.get()
        category = None if category == 'All' or not category else category
        report = self.manager.generate_report(category)
        
        try:
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['Name', 'Category', 'Quantity', 'Price', 'Value', 'Expiry Dates']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(report)
            self.print_output(f"Report exported to {filename}", 'success')
        except Exception as e:
            self.print_output(f"Failed to export report: {str(e)}", 'error')

    def export_data(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not filename:
            return
            
        try:
            self.manager.export_to_json(filename)
            self.print_output(f"Data exported to {filename}", 'success')
        except Exception as e:
            self.print_output(f"Failed to export data: {str(e)}", 'error')

    def import_data(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not filename:
            return
            
        try:
            if self.manager.import_from_json(filename):
                self.print_output(f"Data imported from {filename}", 'success')
                self.update_category_list()
                self.update_report()
            else:
                self.print_output("Failed to import data", 'error')
        except Exception as e:
            self.print_output(f"Error importing data: {str(e)}", 'error')

    def show_about(self):
        about_text = """Inventory Manager Pro v2.0
A comprehensive inventory management solution
with expiry tracking and reporting features.

Developed using Python and Tkinter"""
        messagebox.showinfo("About", about_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryApp(root)
    
    # Configure window resizing
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    
    root.mainloop()