import numpy as np
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from gui import *
from backend import *

fig = None
ax = None
canvas = None
vertical_line = None
last_xdata = None
mouse_move_cid = None 

chart_frame = None

current_year = datetime.datetime.now().year
last_month = datetime.datetime.now().replace(day=1) - datetime.timedelta(days=1)
end_year = last_month.strftime('%Y-%m')

def set_dynamic_title(ax, title, loc='left', color='#5cc4fc', pad=15, base_fontsize=15, max_length=37):
    if len(title) > max_length:
        fontsize = base_fontsize - (len(title) - max_length) // 2
        fontsize = max(fontsize, 10)  # make sure  font size is not too small
    else:
        fontsize = base_fontsize
    ax.set_title(title, loc=loc, fontsize=fontsize, color=color, pad=pad)

def format_yaxis(value, tick_number):
    return f'{value:.2f}'

def destroy_chart():
    if chart_frame:
        chart_frame.destroy()

def display_stock_info(fig, stock_data):
    info_ax = fig.add_axes([0.125, 0.02, 0.775, 0.15])
    info_ax.axis('off')
    latest_data = stock_data[-1]
    info_text = (
        f"Open: {latest_data['open']:.2f}   "
        f"High: {latest_data['high']:.2f}   "
        f"Low: {latest_data['low']:.2f}   "
        f"Close: {latest_data['close']:.2f}\n"
        f"Volume: {latest_data['volume']:,.0f}   "
        f"52W High: {max(d['high'] for d in stock_data):.2f}   "
        f"52W Low: {min(d['low'] for d in stock_data):.2f}"
    )
    info_ax.text(0.5, 0.5, info_text, ha='center', va='center', color='#5cc4fc', fontsize=10)

def handle_stock_data(period, stock_symbol_var, stock_composite_combobox, result_label):
    symbol = stock_symbol_var.get()
    comp_symbol = stock_composite_combobox.get()
    
    if not symbol:
        result_label.config(text="Please select a stock")
        return None

    if comp_symbol == "DAX":
        symbol = symbol.replace(".DE", "") + ".XETRA"
        
    historical_data = fetch_stock_data(symbol, period)
    period_c = get_composite_period(period)
    historical_comp_data = fetch_historical_index_data(comp_symbol, period_c, "1d")
    
    if not historical_data or not historical_comp_data:
        handle_data_fetch_error(historical_data, historical_comp_data, comp_symbol)
        return None

    dates, rates = process_historical_data(historical_data)
    dates_c, rates_c = process_historical_data(historical_comp_data)
    # remove .xetra from symbol name if dax is selected - api requires .de
    symbol = symbol.replace(".XETRA", "") + ".DE" if comp_symbol == "DAX" else symbol
    symbol_name = get_stock_name(symbol)
    title = f'Stock Data for {symbol_name} against {"DAX" if comp_symbol == "DAX" else comp_symbol}'
    ylabel = "Stock Price"
    
    return dates, rates, dates_c, rates_c, title, ylabel, historical_data, historical_comp_data

def handle_currency_data(period, from_currency_combobox, to_currency_combobox, results_label):
    from_currency = from_currency_combobox.get()
    to_currency = to_currency_combobox.get()
    
    if not from_currency or not to_currency:
        result_label.config(text="Please select both currencies")
        return None

    currency_pair = f"{from_currency}/{to_currency}"
    historical_data = fetch_currency_data(currency_pair, period)

    if historical_data is None:
        result_label.config(text="Error fetching historical data")
        return None

    dates, rates = process_currency_data(historical_data)
    title = f'Currency Data for {currency_pair}'
    ylabel = "Exchange Rate"

    return dates, rates, title, ylabel, historical_data

def handle_macro_data(period, region_combobox, macro_economic_combobox, result_label, gdp_metric_combobox, gov_metric_combobox):
    country_code = region_combobox.get()
    region_name = get_region_name(country_code)
    macro_indicator = macro_economic_combobox.get()

    if macro_indicator == "Inflation":
        return handle_inflation_data(period, region_name, region_combobox, result_label)
    elif macro_indicator in ["GDP", "Unemployment Rate", "Government Finances"]:
        return handle_economic_data(period, region_name, macro_indicator, region_combobox, result_label, gdp_metric_combobox, gov_metric_combobox)
    elif macro_indicator == "Interest Rates":
        return handle_interest_rate_data(period, region_name, region_combobox, result_label)

def get_composite_period(period):
    period_map = {"1M": "1mo", "3M": "3mo", "YTD": "ytd", "1Y": "1y"}
    return period_map.get(period, period)

def handle_data_fetch_error(historical_data, historical_comp_data, comp_symbol):
    if not historical_data:
        print("Error: No data returned from fetch_stock_data")
        result_label.config(text="Error fetching historical data")
    elif not historical_comp_data:
        print(f"Error: No data returned for composite index {comp_symbol}")
        result_label.config(text=f"Error fetching data for {comp_symbol}")

def process_historical_data(data):
    dates, rates = [], []
    for item in data:
        try:
            date = datetime.datetime.strptime(item['date'], '%Y-%m-%d')
            try:
                rate = round(item['close'], 4)
            except KeyError:
                rate = round(item['value'], 2)
            dates.append(date)
            rates.append(rate)
        except ValueError:
            print(f"Error parsing date: {item['date']}")
    return dates, rates

def process_currency_data(data):
    dates, rates = [], []
    for i in range(len(data['dates'])):
        try:
            date = datetime.datetime.strptime(data['dates'][i], '%Y-%m-%d')
            rate = data['rates'][i]
            dates.append(date)
            rates.append(rate)
        except ValueError:
            print(f"Error parsing date: {data['dates'][i]}")
    return dates, rates

def get_region_name(country_code):
    region_names = {
        "US": "United States",
        "GB": "UK",
        "DE": "Germany's",
        "JP": "Japan's",
        "FR": "France's"
    }
    return region_names.get(country_code, "Unknown")

def handle_inflation_data(period, region_name, region_combobox, result_label):
    start_year, end_year = get_date_range(period)
    historical_data = get_price_index_data("Inflation", region_combobox.get(), start_year, end_year)
    
    if not historical_data:
        result_label.config(text="Error fetching historical data")
        return None

    dates, rates = process_historical_data(historical_data)
    title = f'{region_name} inflation rate'
    ylabel = "Base year 2010 = 100"

    return dates, rates, title, ylabel, historical_data

def handle_economic_data(period, region_name, indicator, region_combobox, result_label, gdp_metric_combobox, gov_metric_combobox):
    start_year, end_year = get_date_range(period)
    country_code = region_combobox.get()
    
    if indicator == "GDP":
        historical_data = get_economic_data(country_code, gdp_metric_combobox.get(), start_year, end_year)
        title, ylabel = get_gdp_labels(region_name, gdp_metric_combobox)
    elif indicator == "Unemployment Rate":
        historical_data = get_economic_data(country_code, indicator, start_year, end_year)
        title = f'{region_name} Unemployment Rate'
        ylabel = "Unemployment Rate (%)"
    else:  # gov finances
        historical_data = get_economic_data(country_code, gov_metric_combobox.get(), start_year, end_year)
        title = f'{region_name} {gov_metric_combobox.get()}'
        ylabel = "percent of GDP (%)"

    if not historical_data:
        result_label.config(text=f"Error fetching {indicator} data")
        return None

    dates, rates = process_economic_data(historical_data)
    return dates, rates, title, ylabel, historical_data

def handle_interest_rate_data(period, region_name, region_combobox, result_label):
    start_year, end_year = get_date_range(period)
    country_code = region_combobox.get()
    historical_data = get_interest_rate_data(country_code, start_year, end_year)
    
    if historical_data is None:
        result_label.config(text="Error fetching interest rate data")
        return None

    dates, rates = process_historical_data(historical_data)
    title = f'{region_name} Interest Rate'
    ylabel = "Interest Rate (%)"

    return dates, rates, title, ylabel, historical_data

def get_date_range(period):
    current_year = datetime.datetime.now().year
    last_month = datetime.datetime.now().replace(day=1) - datetime.timedelta(days=1)
    
    if period == "5Y":
        return str(current_year - 5), last_month.strftime('%Y-%m')
    elif period == "10Y":
        return str(current_year - 10), str(current_year)
    elif period == "20Y":
        return str(current_year - 20), str(current_year)
    elif period == "30Y":
        return str(current_year - 30), str(current_year)
    elif period == "40Y":
        return str(current_year - 40), str(current_year)
    elif period == "Max":
        return str(current_year - 100), str(current_year)
    else:
        return str(current_year - 5), str(current_year)  # default to  5Y

def process_economic_data(data):
    dates, rates = [], []
    for item in data:
        try:
            date = datetime.datetime.strptime(item['date'], '%Y')
            rate = round(item['value'], 2)
            dates.append(date)
            rates.append(rate)
        except ValueError:
            print(f"Error parsing date: {item['date']}")
    return dates, rates

def get_gdp_labels(region_name, gdp_metric_combobox):
    gdp_metric = gdp_metric_combobox.get()
    if gdp_metric == "Nominal GDP":
        return f'{region_name} GDP', "GDP (in billions USD)"
    elif gdp_metric == "Real GDP Growth":
        return f'{region_name} Real GDP', "GDP Growth Rate (%)"
    elif gdp_metric == "GDP Per Capita":
        return f'{region_name} GDP Per Capita', "GDP Per Capita (in USD)"
    else:
        return f'{region_name} GDP', "GDP"


def create_chart(root, period, financial_data_combobox, from_currency_combobox, to_currency_combobox, region_combobox, macro_economic_combobox, result_label, stock_symbol_var, stock_composite_combobox, gdp_metric_combobox, gov_metric_combobox):
    stockBool = False
    currencyBool = False
    global chart_frame, fig, ax, canvas
    if 'chart_frame' in globals() and chart_frame:
        for widget in chart_frame.winfo_children():
            widget.destroy()
        chart_frame.destroy()
    
    if 'fig' in globals():
        plt.close(fig)
    destroy_chart()
    chart_frame = tk.Frame(root, bg='black')
    chart_frame.pack(pady=8, padx=10, fill=tk.BOTH, expand=True)
    
    selected_financial_data = financial_data_combobox.get()
    
    if selected_financial_data == "Stock":
        data = handle_stock_data(period, stock_symbol_var, stock_composite_combobox, result_label)
        if data:
            dates, rates, dates_c, rates_c, title, ylabel, historical_data, historical_comp_data = data
            stockBool = True
        else:
            return
    elif selected_financial_data == "Currency":
        data = handle_currency_data(period, from_currency_combobox, to_currency_combobox, result_label)
        if data:
            dates, rates, title, ylabel, historical_data = data
            currencyBool = True
        else:
            return
    elif selected_financial_data == "Macro-Economic Indicators":
        data = handle_macro_data(period, region_combobox, macro_economic_combobox, result_label, gdp_metric_combobox, gov_metric_combobox)
        if data:
            dates, rates, title, ylabel, historical_data = data
        else:
            return
    else:
        print("Error: Invalid financial data type selected")
        result_label.config(text="Invalid financial data type selected")
        return

    if not dates:
        print("Error: No valid historical data available")
        result_label.config(text="No valid historical data available")
        return

    # sort the data by date
    sorted_data = sorted(zip(dates, rates))
    dates, rates = zip(*sorted_data)

    # create new figure and axis
    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
    if stockBool:
        display_stock_info(fig, historical_data)

    plt.subplots_adjust(bottom=0.25)

    line_color = '#5cc4fc'
    fill_color = '#5cc4fc'
    
    if stockBool:
        if not dates_c or not rates_c:
            result_label.config(text="No valid composite data available")
        else:
            sorted_comp_data = sorted(zip(dates_c, rates_c))
            dates_c, rates_c = zip(*sorted_comp_data)
            # create second y-axis and plot data 
            ax2 = ax.twinx()
            comp_line_color = 'red'
            comp_line, = ax2.plot(dates_c, rates_c, color=comp_line_color, linewidth=2)
            # set color
            ax2.spines['right'].set_color(comp_line_color)
            ax2.tick_params(axis='y', colors=comp_line_color)
            
            ax.set_zorder(ax2.get_zorder() + 1)
            ax.patch.set_visible(False)  

    # plot  main data on the (primary) axis
    main_line, = ax.plot(dates, rates, color=line_color, linewidth=2)
    fill_between = ax.fill_between(dates, rates, min(rates), alpha=0.1, color=fill_color)
    # set color
    ax.set_facecolor('#222222')
    fig.patch.set_facecolor('#222222')
    
    # set stock line above the composite line
    main_line.set_zorder(3)
    fill_between.set_zorder(2)
    if stockBool and 'comp_line' in locals():
        comp_line.set_zorder(1)
    # set x-axis labels based on the period
    if period in ["5Y", "10Y", "20Y", "40Y", "Max", "30Y"]:
        ax.xaxis.set_major_formatter(DateFormatter("%Y"))
    elif period in ["YTD", "1Y"]:
        ax.xaxis.set_major_formatter(DateFormatter("%b"))
    else:
        ax.xaxis.set_major_formatter(DateFormatter("%b %d"))
    
    plt.xticks(rotation=45, ha='right')
    
    import matplotlib.ticker as ticker
    
    # format y axis data based on the range
    y_min, y_max = min(rates), max(rates)
    y_range = y_max - y_min
    
    def custom_formatter(x, pos):
        if y_range > 5:
            return f'{int(x)}'
        else:
            return f'{x:.3g}'
    
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(custom_formatter))
    
    # remove disconnected areas for x and y axis
    ax.set_ylim([y_min - 0.01 * y_range, y_max + 0.01 * y_range])
    
    ax.set_xlim([dates[0], dates[-1]])
    
    # set color of spines (bottom and left)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(line_color)
    ax.spines['bottom'].set_color(line_color)
    
    # use custom title function if stock selected - 
    #      size of company name varies and needs to be adjusted dynamically so it can fit
    if stockBool:
        set_dynamic_title(ax, title, loc='left', color=line_color, pad=20)
    else:
        ax.set_title(title, loc='left', fontsize=16, color='#5cc4fc', pad=20)
    ax.spines['top'].set_visible(False)
    
    ax.set_xlabel('')
    ax.set_ylabel(ylabel, color=line_color, rotation=90, labelpad=10)
    
    # set color of the tick labels and axis labels to white
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color(line_color)
    
    #  add padding at the bottom
    plt.subplots_adjust(bottom=0.2)
    
    canvas = FigureCanvasTkAgg(fig, master=chart_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # ensure matplotlib closes when user closes the window
    def on_closing():
        plt.close(fig)
        root.quit()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    #  vertical line for mouse hover
    vertical_line = ax.axvline(color=line_color, linewidth=1, linestyle='--', alpha=0.7)
    vertical_line.set_visible(False)

    #  circle marker for mouse hover
    marker, = ax.plot([], [], 'o', color=line_color, markersize=8, markeredgecolor='black', markeredgewidth=1.5)
    marker.set_visible(False)
    text_annotation = ax.text(0, 0, '', color='white', fontweight='bold', ha='center', va='bottom')
    text_annotation.set_visible(False)

    # add two marker for click &drag 
    click_marker, = ax.plot([], [], 'o', color='red', markersize=8, markeredgecolor='black', markeredgewidth=1.5)
    click_marker.set_visible(False)
    click_text = ax.text(0, 0, '', color='white', fontweight='bold', ha='center', va='bottom')
    click_text.set_visible(False)

    difference_text = ax.text(0.98, 1.02, '', color='white', fontsize=10, transform=ax.transAxes, va='bottom', ha='right')
    difference_text.set_visible(False)

    # add rectangle for coloring/highlighting  a given region
    highlight_rect = plt.Rectangle((0, 0), 0, 1, facecolor='green', alpha=0.2)
    ax.add_patch(highlight_rect)
    highlight_rect.set_visible(False)

    is_clicked = False
    is_dragging = False
    click_x, click_y = None, None
    original_color = line_color
    original_alpha = 0.1
    highlighted_line = None
    start_marker, end_marker = None, None
    start_text, end_text = None, None
    date_text = None
    
    def update_chart_colors(start_date, end_date, is_increase):
        nonlocal highlighted_line, start_marker, end_marker, start_text, end_text, date_text
        color = 'green' if is_increase else 'red'
        highlight_rect.set_facecolor(color)
        highlight_rect.set_xy((mdates.date2num(start_date), ax.get_ylim()[0]))
        highlight_rect.set_width(mdates.date2num(end_date) - mdates.date2num(start_date))
        highlight_rect.set_height(ax.get_ylim()[1] - ax.get_ylim()[0])
        highlight_rect.set_visible(True)
    
        # reduce  main line and the area underneath opacity
        main_line.set_alpha(0.3)
        fill_between.set_alpha(0.05)

        # remove any previous highlighted lines and markers (prevent overlap)
        if highlighted_line:
            highlighted_line.remove()
        if start_marker:
            start_marker.remove()
        if end_marker:
            end_marker.remove()
        if start_text:
            start_text.remove()
        if end_text:
            end_text.remove()
        if date_text:
            date_text.remove()
    
        # highlight the selected region for the main stock data
        selected_dates = [date for date in dates if min(start_date, end_date) <= date <= max(start_date, end_date)]
        selected_rates = [rates[dates.index(date)] for date in selected_dates]
        highlighted_line, = ax.plot(selected_dates, selected_rates, color=line_color, linewidth=2, zorder=3)
    
        # add markers and text for start and end points
        start_value = round(selected_rates[0], 3)
        end_value = round(selected_rates[-1], 3)
        
        # calc vertical position for text
        y_range = ax.get_ylim()[1] - ax.get_ylim()[0]
        text_height = y_range * 0.05
        
        if abs(mdates.date2num(selected_dates[-1]) - mdates.date2num(selected_dates[0])) < (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.1:
            start_y = max(start_value, end_value) + text_height
            end_y = start_y + text_height
        else:
            start_y = start_value
            end_y = end_value
    
        start_marker, = ax.plot(selected_dates[0], start_value, 'o', color=color, markersize=8, markeredgecolor='black', markeredgewidth=1.5, zorder=4)
        end_marker, = ax.plot(selected_dates[-1], end_value, 'o', color=color, markersize=8, markeredgecolor='black', markeredgewidth=1.5, zorder=4)
        if currencyBool:
            start_text = ax.text(selected_dates[0], start_y, f'{start_value:.3f}', color='white', fontweight='bold', ha='center', va='bottom', fontsize=10, zorder=4)
            end_text = ax.text(selected_dates[-1], end_y, f'{end_value:.3f}', color='white', fontweight='bold', ha='center', va='bottom', fontsize=10, zorder=4)
        else:
            start_text = ax.text(selected_dates[0], start_y, f'{start_value:.2f}', color='white', fontweight='bold', ha='center', va='bottom', fontsize=10, zorder=4)
            end_text = ax.text(selected_dates[-1], end_y, f'{end_value:.2f}', color='white', fontweight='bold', ha='center', va='bottom', fontsize=10, zorder=4)
        
        # add date range text
        date_format = "%d %b %Y"
        date_text = ax.text(0.5, 1.02, f"{start_date.strftime(date_format)} - {end_date.strftime(date_format)}", 
                            transform=ax.transAxes, ha='center', va='bottom', fontsize=10, color='white')

    def reset_chart_colors():
        nonlocal highlighted_line, start_marker, end_marker, start_text, end_text, date_text
        highlight_rect.set_visible(False)
        main_line.set_alpha(1)
        fill_between.set_alpha(original_alpha)
        if highlighted_line:
            highlighted_line.remove()
            highlighted_line = None
        if start_marker:
            start_marker.remove()
            start_marker = None
        if end_marker:
            end_marker.remove()
            end_marker = None
        if start_text:
            start_text.remove()
            start_text = None
        if end_text:
            end_text.remove()
            end_text = None
        if date_text:
            date_text.remove()
            date_text = None

    def on_mouse_move(event):
        nonlocal is_clicked, is_dragging, click_x, click_y
        if event.inaxes == ax:
            # update vertical line
            vertical_line.set_xdata([event.xdata, event.xdata])
            vertical_line.set_visible(True)

            # find closest x value (date) to mouse position
            idx = np.searchsorted(mdates.date2num(dates), event.xdata, side="left")
            if idx > 0 and (idx == len(dates) or abs(event.xdata - mdates.date2num(dates[idx-1])) < abs(event.xdata - mdates.date2num(dates[idx]))):
                idx -= 1

            x = dates[idx]
            y = rates[idx]

            # update marker position
            marker.set_data([x], [y])
            marker.set_visible(True)

            if not is_dragging:
                # update text annotation at the top only when not dragging
                text_annotation.set_position((mdates.date2num(x), ax.get_ylim()[1]))
                
                if currencyBool: # set text to 3 decimal places for currency, 2 for others
                    text_annotation.set_text(f'{y:.3f}')
                else:
                    text_annotation.set_text(f'{y:.2f}')
                text_annotation.set_visible(True)
            else:
                # hide top text  when dragging
                text_annotation.set_visible(False)
                
                # calc differences and update difference text
                days_diff = abs((x - click_x).days)
                value_diff = y - click_y
                percentage_diff = (y - click_y) / click_y * 100
                difference_text.set_text(f'Days: {days_diff}\nValue: {value_diff:.2f}\nChange: {percentage_diff:.2f}%')
                difference_text.set_visible(True)
                update_chart_colors(click_x, x, value_diff > 0)

            fig.canvas.draw_idle()
        else:
            vertical_line.set_visible(False)
            marker.set_visible(False)
            text_annotation.set_visible(False)
            if not is_dragging:
                click_marker.set_visible(False)
                click_text.set_visible(False)
                difference_text.set_visible(False)
                reset_chart_colors()
            fig.canvas.draw_idle()
                
    def on_click(event):
        nonlocal is_clicked, click_x, click_y
        main_line.set_alpha(0.3)
        fill_between.set_alpha(0.05)
        if event.inaxes == ax:
            is_clicked = True
            idx = np.searchsorted(mdates.date2num(dates), event.xdata, side="left")
            if idx > 0 and (idx == len(dates) or abs(event.xdata - mdates.date2num(dates[idx-1])) < abs(event.xdata - mdates.date2num(dates[idx]))):
                idx -= 1
        
            click_x = dates[idx]
            click_y = rates[idx]

            if click_y != 0:
                click_y = round(click_y, 3 - int(np.floor(np.log10(abs(click_y)))) - 1)
            else:
                click_y = 0  

            marker.set_data([click_x], [click_y])
            marker.set_visible(True)
            text_annotation.set_position((mdates.date2num(click_x), click_y))
            text_annotation.set_text(f'{click_y:.2f}')
            text_annotation.set_visible(True)

            canvas.draw_idle()

    def on_motion(event):
        nonlocal is_dragging
        if is_clicked and event.inaxes == ax:
            is_dragging = True

    def on_release(event):
        nonlocal is_clicked, is_dragging
        is_clicked = False
        is_dragging = False
        difference_text.set_visible(False)
        reset_chart_colors()
    
        # show  top text annotation again when user releases mouse
        if event.inaxes == ax:
            idx = np.searchsorted(mdates.date2num(dates), event.xdata, side="left")
            if idx > 0 and (idx == len(dates) or abs(event.xdata - mdates.date2num(dates[idx-1])) < abs(event.xdata - mdates.date2num(dates[idx]))):
                idx -= 1
            x = dates[idx]
            y = rates[idx]
            text_annotation.set_position((mdates.date2num(x), ax.get_ylim()[1]))
            if currencyBool:
                text_annotation.set_text(f'{y:.3f}')
            else:
                text_annotation.set_text(f'{y:.2f}')
            text_annotation.set_visible(True)
    
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect('motion_notify_event', on_mouse_move)
    fig.canvas.mpl_connect('button_press_event', on_click)
    fig.canvas.mpl_connect('button_release_event', on_release)
    fig.canvas.mpl_connect('motion_notify_event', on_motion)


