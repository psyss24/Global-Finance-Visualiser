
# imports
import tkinter as tk
import ttkbootstrap as ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from backend import *
from chart import *


class GlobalFinanceVisualizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GFV - v1")
        self.root.geometry("750x700")
        self.root.configure(bg='black')
        self.size_flag = True
        self.stock_symbol_var = tk.StringVar()
        self.setup_style()
        self.create_title()
        self.create_main_input_frame()
        self.create_currency_input_frame()
        self.create_result_label()
        self.create_period_buttons()
        self.update_ui()


    def setup_style(self):
        self.style = ttk.Style()
        self.style.theme_use('darkly')
        self.style.configure('TLabel', background='black', foreground='white')
        self.style.configure('TEntry', fieldbackground='black', foreground='white')
        self.style.configure('TCombobox', fieldbackground='black', foreground='white')
        self.style.map('TCombobox', fieldbackground=[('readonly', 'black')], foreground=[('readonly', 'white')])
        self.style.configure('TButton', background='black', foreground='white')
        self.style.map('TButton', background=[('active', 'black')], foreground=[('active', 'white')])

    def create_title(self):
        title_label = tk.Label(self.root, text="Global Finance Visualizer", font=("Helvetica", 23), bg='#5cc4fc', fg='#5cc4fc')
        title_label.pack(pady=4)

    def create_main_input_frame(self):
        self.main_input_frame = tk.Frame(self.root, bg='black', pady=4)
        self.main_input_frame.pack()

        self.create_financial_data_frame()
        self.create_macro_economic_frame()
        self.create_region_frame()
        self.create_gdp_metric_frame()
        self.create_gov_metric_frame()
        self.create_stock_composite_frame()
        self.create_stock_search_frame()

    def create_financial_data_frame(self):
        financial_data_frame = tk.Frame(self.main_input_frame, bg='black')
        financial_data_label = tk.Label(master=financial_data_frame, text="Financial Data", bg='black', fg='white', anchor='w')
        self.financial_data_combobox = ttk.Combobox(master=financial_data_frame, values=["Currency", "Stock", "Macro-Economic Indicators"], style='TCombobox', state='readonly')
        self.financial_data_combobox.current(0)
        financial_data_label.pack(side='top', pady=4, anchor='w')
        self.financial_data_combobox.pack(side='top', pady=4)
        financial_data_frame.pack(side='left', padx=10)

        self.financial_data_combobox.bind("<<ComboboxSelected>>", lambda e: self.update_ui())

    def create_macro_economic_frame(self):
        self.macro_economic_frame = tk.Frame(self.main_input_frame, bg='black')
        macro_economic_label = tk.Label(master=self.macro_economic_frame, text="Select Indicator", bg='black', fg='white', anchor='w')
        self.macro_economic_combobox = ttk.Combobox(master=self.macro_economic_frame, values=["Inflation", "Interest Rates", "Unemployment Rate", "GDP", "Government Finances"], width=15, style='TCombobox', state='readonly')
        self.macro_economic_combobox.current(0)
        macro_economic_label.pack(side='top', pady=4, anchor='w')
        self.macro_economic_combobox.pack(side='top', pady=4)
        self.macro_economic_frame.pack(side='left', padx=10)

        self.macro_economic_combobox.bind("<<ComboboxSelected>>", lambda e: self.update_ui())

    def create_region_frame(self):
        self.region_frame = tk.Frame(self.main_input_frame, bg='black')
        region_label = tk.Label(master=self.region_frame, text="Select Region", bg='black', fg='white', anchor='w')
        self.region_combobox = ttk.Combobox(master=self.region_frame, values=["GB", "US", "FR", "DE", "JP"], width=5, style='TCombobox', state='readonly')
        self.region_combobox.current(0)
        region_label.pack(side='top', pady=4, anchor='w')
        self.region_combobox.pack(side='top', pady=4)

    def create_gdp_metric_frame(self):
        self.gdp_metric_frame = tk.Frame(self.main_input_frame, bg='black')
        gdp_metric_label = tk.Label(master=self.gdp_metric_frame, text="Select GDP Metric", bg='black', fg='white', anchor='w')
        self.gdp_metric_combobox = ttk.Combobox(master=self.gdp_metric_frame, values=["Nominal GDP", "Real GDP Growth", "GDP Per Capita"], style='TCombobox', state='readonly')
        self.gdp_metric_combobox.current(0)
        gdp_metric_label.pack(side='top', pady=4, anchor='w')
        self.gdp_metric_combobox.pack(side='top', pady=4)
        self.gdp_metric_frame.pack(side='left', padx=10)

    def create_gov_metric_frame(self):
        self.gov_metric_frame = tk.Frame(self.main_input_frame, bg='black')
        gov_metric_label = tk.Label(master=self.gov_metric_frame, text="Select Government Fiscal Data", bg='black', fg='white', anchor='w')
        self.gov_metric_combobox = ttk.Combobox(master=self.gov_metric_frame, values=["Government debt", "Government revenue", "Government expenditure"], style='TCombobox', state='readonly')
        self.gov_metric_combobox.current(0)
        gov_metric_label.pack(side='top', pady=4, anchor='w')
        self.gov_metric_combobox.pack(side='top', pady=4)
        self.gov_metric_frame.pack(side='left', padx=10)

    def create_stock_composite_frame(self):
        self.stock_composite_frame = tk.Frame(self.main_input_frame, bg='black')
        stock_composite_label = tk.Label(self.stock_composite_frame, text="Stock Composite", bg='black', fg='white', anchor='w')
        self.stock_composite_combobox = ttk.Combobox(self.stock_composite_frame, values=list(all_tickers.keys()), style='TCombobox', state='readonly')
        self.stock_composite_combobox.current(0)
        stock_composite_label.pack(side='top', pady=4, anchor='w')
        self.stock_composite_combobox.pack(side='top', pady=4)
        self.stock_composite_frame.pack(side='left', padx=10)

        self.stock_composite_combobox.bind("<<ComboboxSelected>>", self.update_stock_search_dropdown)

    def create_stock_search_frame(self):
        self.stock_search_frame = tk.Frame(self.main_input_frame, bg='black')
        stock_search_label = tk.Label(self.stock_search_frame, text="Search Stock Symbol", bg='black', fg='white', anchor='w')
        self.stock_search_var = tk.StringVar()
        self.stock_search_entry = ttk.Entry(self.stock_search_frame, textvariable=self.stock_search_var, style='TEntry')
        self.stock_search_results = ttk.Combobox(self.stock_search_frame, style='TCombobox', state='readonly')
        stock_search_label.pack(side='top', pady=4, anchor='w')
        self.stock_search_entry.pack(side='top', pady=4)
        self.stock_search_results.pack(side='top', pady=4)
        self.stock_search_frame.pack(side='left', padx=10)

        self.stock_search_entry.bind('<KeyRelease>', self.search_stock_symbols)
        self.stock_search_results.bind("<<ComboboxSelected>>", self.update_stock_symbol)
        self.stock_symbol_var = tk.StringVar()

    def create_currency_input_frame(self):
        self.currency_input_frame = tk.Frame(self.root, bg='black', pady=4)
    
        amount_frame = tk.Frame(self.currency_input_frame, bg='black')
        amount_label = tk.Label(master=amount_frame, text="Amount", bg='black', fg='white', anchor='w')
        self.amount_var = tk.StringVar()
        self.amount_entry = ttk.Entry(master=amount_frame, textvariable=self.amount_var, style='TEntry')
        self.amount_entry.placeholder = False  
        amount_label.pack(side='top', pady=4, anchor='w')
        self.amount_entry.pack(side='top', pady=4)
    
        supported_currencies = ["USD", "EUR", "GBP", "JPY", "CAD"]  
    
        from_currency_frame = tk.Frame(self.currency_input_frame, bg='black')
        from_currency_label = tk.Label(master=from_currency_frame, text="From", bg='black', fg='white', anchor='w')
        self.from_currency_combobox = ttk.Combobox(master=from_currency_frame, values=supported_currencies, style='TCombobox', state='readonly')
        self.from_currency_combobox.current(0)
        from_currency_label.pack(side='top', pady=4, anchor='w')
        self.from_currency_combobox.pack(side='top', pady=4)
    
        to_currency_frame = tk.Frame(self.currency_input_frame, bg='black')
        to_currency_label = tk.Label(master=to_currency_frame, text="To", bg='black', fg='white', anchor='w')
        self.to_currency_combobox = ttk.Combobox(master=to_currency_frame, values=supported_currencies, style='TCombobox', state='readonly')
        self.to_currency_combobox.current(1)
        to_currency_label.pack(side='top', pady=4, anchor='w')
        self.to_currency_combobox.pack(side='top', pady=4)
    
        amount_frame.pack(side='left', padx=10)
        from_currency_frame.pack(side='left', padx=10)
        to_currency_frame.pack(side='left', padx=10)
    
        self.amount_entry.bind("<FocusIn>", self.remove_placeholder)
        self.amount_entry.bind("<FocusOut>", self.update_placeholder)
        self.from_currency_combobox.bind("<<ComboboxSelected>>", lambda event: [self.update_placeholder(), self.update_result()])
        self.to_currency_combobox.bind("<<ComboboxSelected>>", lambda event: [self.update_placeholder(), self.update_result()])
        self.amount_entry.bind("<KeyRelease>", lambda event: self.update_result())
    
        self.update_placeholder()
    def create_result_label(self):
        self.result_label = tk.Label(self.root, text="", bg='black', fg='white')
        self.result_label.pack(pady=3)

    def create_period_buttons(self):
        self.button_frame = tk.Frame(self.root, bg='black')
        self.button_frame.pack(pady=4)
        self.update_period_buttons()

    def on_button_click(self, period):
        self.destroy_chart() 
        if self.size_flag:
            self.root.geometry("751x703")
        else:
            self.root.geometry("752x702")

        create_chart(
            self.root,
            period,
            self.financial_data_combobox,
            self.from_currency_combobox,
            self.to_currency_combobox,
            self.region_combobox,
            self.macro_economic_combobox,
            self.result_label,
            self.stock_symbol_var,
            self.stock_composite_combobox,
            self.gdp_metric_combobox,
            self.gov_metric_combobox
        )  

        self.size_flag = not self.size_flag

    def update_period_buttons(self):
        for widget in self.button_frame.winfo_children():
            widget.destroy()

        periods = ["1M", "3M", "YTD", "1Y"]
        if self.financial_data_combobox.get() == "Macro-Economic Indicators":
            periods = ["5Y", "10Y", "20Y", "40Y"]

            if self.macro_economic_combobox.get() == "Unemployment Rate":
                periods = ["5Y", "10Y", "20Y", "40Y"]
            elif self.macro_economic_combobox.get() == "GDP":
                periods = ["5Y", "10Y", "20Y", "Max"]
            elif self.macro_economic_combobox.get() == "Government Finances":
                periods = ["5Y", "10Y", "20Y", "30Y"]

        for period in periods:
            button = ttk.Button(self.button_frame, text=period, command=lambda p=period: self.on_button_click(p), style='TButton')
            button.pack(side='left', padx=5)

    def update_ui(self, event=None):
        selected_financial_data = self.financial_data_combobox.get()
        selected_macro_indicator = self.macro_economic_combobox.get()

        # destroy  chart if it already was created 
        self.destroy_chart()

        # Hide all frames initially
        self.currency_input_frame.pack_forget()
        self.stock_composite_frame.pack_forget()
        self.stock_search_frame.pack_forget()
        self.macro_economic_frame.pack_forget()
        self.region_frame.pack_forget()
        self.gdp_metric_frame.pack_forget()
        self.gov_metric_frame.pack_forget()

        self.clear_result_label()

        if selected_financial_data == "Currency":
            self.currency_input_frame.pack(after=self.main_input_frame)
        elif selected_financial_data == "Stock":
            self.stock_composite_frame.pack(side='left', padx=10, in_=self.main_input_frame)
            self.stock_search_frame.pack(side='left', padx=10, in_=self.main_input_frame)
            self.stock_composite_combobox.set("S&P 500")
            self.update_stock_search_dropdown(None)
        elif selected_financial_data == "Macro-Economic Indicators":
            self.macro_economic_frame.pack(side='left', padx=10, in_=self.main_input_frame)
            self.region_frame.pack(side='left', padx=10, in_=self.main_input_frame)
            if selected_macro_indicator == "GDP":
                self.gdp_metric_frame.pack(side='left', padx=10, in_=self.main_input_frame)
            elif selected_macro_indicator == "Government Finances":
                self.gov_metric_frame.pack(side='left', padx=10, in_=self.main_input_frame)

        self.update_period_buttons()
        self.root.update_idletasks()


    def destroy_chart(self):
        if hasattr(self, 'chart_frame') and self.chart_frame:
            for widget in self.chart_frame.winfo_children():
                widget.destroy()
            self.chart_frame = None

    def update_stock_search_dropdown(self, event=None):
        selected_composite = self.stock_composite_combobox.get()
        if selected_composite in all_tickers:
            tickers_with_names = [f"{ticker} - {company_name}" for ticker, company_name in all_tickers[selected_composite]]
            self.stock_search_results['values'] = tickers_with_names
            if tickers_with_names:
                self.stock_search_results.current(0)  
                selected_item = self.stock_search_results.get()
                if selected_item:
                    symbol = selected_item.split(' - ')[1].strip()
                    self.stock_symbol_var.set(symbol)
        else:
            self.stock_search_results['values'] = []

    def search_stock_symbols(self, event): 
        search_term = self.stock_search_entry.get().lower()  
        selected_composite = self.stock_composite_combobox.get()  
        if selected_composite in all_tickers:
            matching_tickers = [f"{ticker} - {company_name}" for ticker, company_name in all_tickers[selected_composite] if search_term in ticker.lower() or search_term in company_name.lower()]
            self.stock_search_results['values'] = matching_tickers  
            if matching_tickers:
                self.stock_search_results.current(0)  
                selected_item = self.stock_search_results.get()  
                if selected_item:
                    symbol = selected_item.split(' - ')[1].strip()
                    self.stock_symbol_var.set(symbol)  
        else:
            self.stock_search_results['values'] = []  

    # currency conversions in ui
    def update_result(self):
        try:
            amount_str = self.amount_var.get()
            if not amount_str or not amount_str.replace('.', '', 1).isdigit():
                self.result_label.config(text="")
                return
            
            amount = float(amount_str)
            from_currency = self.from_currency_combobox.get().encode('utf-8')
            to_currency = self.to_currency_combobox.get().encode('utf-8')
            result = lib.convert_currency(from_currency, to_currency, c_double(amount))
            self.result_label.config(text=f"Result: {result:.2f} {to_currency.decode('utf-8')}")
        except Exception as e:
            self.result_label.config(text=f"Error: {e}")

    def clear_result_label(self):
        self.result_label.config(text="")

    def update_placeholder(self, event=None):
        from_currency = self.from_currency_combobox.get()
        to_currency = self.to_currency_combobox.get()
        try:
            from_currency_encoded = from_currency.encode('utf-8')
            to_currency_encoded = to_currency.encode('utf-8')
            conversion_rate = lib.convert_currency(from_currency_encoded, to_currency_encoded, c_double(1))
            placeholder_text = f"1 {from_currency} = {conversion_rate:.2f} {to_currency}"
        except Exception as e:
            placeholder_text = f"{from_currency} to {to_currency}"
        
        if self.amount_var.get() == "" or self.amount_entry.placeholder:
            self.amount_var.set(placeholder_text)
            self.amount_entry.config(foreground='gray')
            self.amount_entry.placeholder = True

    def remove_placeholder(self, event=None):
        if self.amount_entry.placeholder:
            self.amount_var.set("")
            self.amount_entry.config(foreground='white')
            self.amount_entry.placeholder = False

    def check_for_characters(self, event=None):
        if self.amount_var.get() == "":
            self.update_placeholder()
        else:
            self.amount_entry.config(foreground='white')
            self.amount_entry.placeholder = False

    def update_stock_symbol(self, *args):  
        selected_item = self.stock_search_results.get()  
        if selected_item:
            # split string and get the second part 
            symbol = selected_item.split(' - ')[1].strip()
            self.stock_symbol_var.set(symbol)  
        else:
            self.stock_symbol_var.set('')

def run_gui():
    root = tk.Tk()
    app = GlobalFinanceVisualizerGUI(root)
    root.protocol("WM_DELETE_WINDOW", root.quit)  
    app.update_ui()
    app.update_placeholder() 
    root.mainloop()
