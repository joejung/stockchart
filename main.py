import sys
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QLabel, QSpinBox, QMessageBox
)
from PyQt5.QtCore import Qt

# Ensure the plot doesn't open in a separate window when using PyQt5
plt.ioff()

class StockChartApp(QMainWindow):
    """
    A PyQt5 application to display historical stock prices for GOOGL and NVDA.
    Users can select the start year and time interval (Day, Week, Month, Quarter, Year).
    Includes hover functionality to show price on plot.
    """
    def __init__(self):
        """
        Initializes the main window and sets up the UI components.
        """
        super().__init__()
        self.setWindowTitle("Stock Price Comparison Plotter (GOOGL vs NVDA)")
        self.setGeometry(100, 100, 1000, 700) # Initial window size (width, height)

        self.figure, self.ax = plt.subplots(figsize=(10, 6)) # Matplotlib figure and axes
        self.canvas = FigureCanvas(self.figure) # Canvas to embed matplotlib plot in Qt

        self.annotation = None # To store the annotation object for hover
        self.line_googl = None # To store the plot line for GOOGL
        self.line_nvda = None  # To store the plot line for NVDA

        self.init_ui() # Initialize the User Interface

        # Connect the motion event to the hover handler
        self.canvas.mpl_connect("motion_notify_event", self.on_hover)
        # Connect the leave event to clear the annotation
        self.canvas.mpl_connect("figure_leave_event", self.clear_annotation)


    def init_ui(self):
        """
        Sets up the main layout and widgets for the application.
        """
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Control Panel Layout ---
        control_layout = QHBoxLayout()
        control_layout.setAlignment(Qt.AlignLeft) # Align controls to the left

        # Start Year Input
        control_layout.addWidget(QLabel("Start Year:"))
        self.start_year_input = QSpinBox()
        self.start_year_input.setMinimum(1990) # Set a reasonable minimum year
        self.start_year_input.setMaximum(pd.Timestamp.now().year) # Max year is current year
        self.start_year_input.setValue(pd.Timestamp.now().year - 5) # Default to 5 years ago
        self.start_year_input.setMinimumWidth(80)
        control_layout.addWidget(self.start_year_input)

        # Time Interval Selection
        control_layout.addWidget(QLabel("Interval:"))
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["Day", "Week", "Month", "Quarter", "Year"])
        self.interval_combo.setMinimumWidth(100)
        control_layout.addWidget(self.interval_combo)

        # Plot Button
        self.plot_button = QPushButton("Plot Stock Data")
        self.plot_button.clicked.connect(self.plot_data)
        control_layout.addWidget(self.plot_button)

        # Add a stretch to push controls to the left if space allows
        control_layout.addStretch(1)

        # Add control layout to the main layout
        main_layout.addLayout(control_layout)

        # --- Plotting Area ---
        main_layout.addWidget(self.canvas) # Add the matplotlib canvas to the layout

        # Initial plot on startup
        self.plot_data()

    def fetch_and_resample_data(self, symbol, start_date, interval):
        """
        Fetches historical stock data for a given symbol and resamples it based on the interval.
        Returns a DataFrame with the 'Close' price or an empty DataFrame if an error occurs.
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="max")

            if df.empty:
                QMessageBox.warning(self, "Data Error",
                                    f"No data found for {symbol}."
                                    " Please check the symbol or date range.")
                return pd.DataFrame() # Return empty DataFrame

            # Filter data by start date
            df = df[df.index >= start_date]

            if df.empty:
                # This warning can be a bit aggressive if one stock has no data for the *filtered* period
                # but the other does. Let's make it a general warning in plot_data instead.
                return pd.DataFrame() # Return empty DataFrame, plot_data will handle the message

            # Resample data based on interval
            if interval == "Day":
                # No resampling needed, use daily data
                pass
            elif interval == "Week":
                df = df['Close'].resample('W').last().to_frame()
            elif interval == "Month":
                df = df['Close'].resample('M').last().to_frame()
            elif interval == "Quarter":
                df = df['Close'].resample('Q').last().to_frame()
            elif interval == "Year":
                df = df['Close'].resample('Y').last().to_frame()

            return df
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while fetching {symbol} data: {e}\n"
                                 "Please check your internet connection or try again later.")
            return pd.DataFrame() # Return empty DataFrame

    def plot_data(self):
        """
        Fetches stock data for GOOGL and NVDA, then plots both on the same chart
        with different colors based on user selections.
        """
        # Clear any existing annotation before redrawing the plot
        self.clear_annotation()

        start_year = self.start_year_input.value()
        interval = self.interval_combo.currentText()

        start_date = f"{start_year}-01-01"

        # Fetch data for GOOGL
        self.df_googl = self.fetch_and_resample_data("GOOGL", start_date, interval)
        # Fetch data for NVDA
        self.df_nvda = self.fetch_and_resample_data("NVDA", start_date, interval)

        self.ax.clear() # Clear previous plot

        # Store the lines in instance variables so on_hover can access them
        self.line_googl = None
        self.line_nvda = None

        if not self.df_googl.empty:
            self.line_googl, = self.ax.plot(self.df_googl.index, self.df_googl['Close'],
                                            label='GOOGL Close Price', color='steelblue', linewidth=2)
        else:
            QMessageBox.information(self, "Data Not Available", "Could not fetch GOOGL data for the selected period.")

        if not self.df_nvda.empty:
            self.line_nvda, = self.ax.plot(self.df_nvda.index, self.df_nvda['Close'],
                                           label='NVDA Close Price', color='firebrick', linewidth=2)
        else:
            QMessageBox.information(self, "Data Not Available", "Could not fetch NVDA data for the selected period.")

        if not self.df_googl.empty or not self.df_nvda.empty:
            # Add labels, title, and legend
            self.ax.set_title(f'GOOGL vs NVDA Stock Price ({interval}ly) from {start_year}', fontsize=16)
            self.ax.set_xlabel('Date', fontsize=12)
            self.ax.set_ylabel('Close Price (USD)', fontsize=12)
            self.ax.grid(True, linestyle='--', alpha=0.7)
            self.ax.legend(fontsize=10)

            # Format x-axis dates for better readability
            self.figure.autofmt_xdate()
        else:
            self.ax.text(0.5, 0.5, "No data to display. Adjust year or interval.",
                         horizontalalignment='center', verticalalignment='center',
                         transform=self.ax.transAxes, fontsize=14, color='gray')

        self.canvas.draw_idle() # Redraw the canvas

    def on_hover(self, event):
        """
        Handles mouse motion events to display price annotations.
        """
        if event.inaxes == self.ax:
            # Clear previous annotation
            self.clear_annotation()

            found_point = False
            # Check GOOGL line
            if self.line_googl and not self.df_googl.empty:
                contains, info = self.line_googl.contains(event)
                if contains:
                    ind = info['ind'][0] # Get the index of the closest point
                    date = self.df_googl.index[ind]
                    price = self.df_googl['Close'].iloc[ind]
                    self.show_annotation(date, price, "GOOGL", event.xdata, event.ydata)
                    found_point = True

            # Check NVDA line if no GOOGL point was found near the cursor
            if not found_point and self.line_nvda and not self.df_nvda.empty:
                contains, info = self.line_nvda.contains(event)
                if contains:
                    ind = info['ind'][0]
                    date = self.df_nvda.index[ind]
                    price = self.df_nvda['Close'].iloc[ind]
                    self.show_annotation(date, price, "NVDA", event.xdata, event.ydata)
                    found_point = True

            if not found_point:
                # If no point found, ensure annotation is cleared
                self.clear_annotation()

        else:
            # If mouse is outside the axes, clear the annotation
            self.clear_annotation()

    def show_annotation(self, date, price, symbol, x_data, y_data):
        """
        Displays an annotation with the date, price, and symbol.
        """
        # Format the date nicely
        formatted_date = date.strftime('%Y-%m-%d')
        text = f"{symbol}\nDate: {formatted_date}\nPrice: ${price:.2f}"

        # Get the pixel coordinates of the data point for annotation placement
        # The x_data and y_data from the event are already in data coordinates
        # We adjust xytext to be an offset from the data point
        self.annotation = self.ax.annotate(text,
                                            xy=(x_data, y_data),
                                            xytext=(10, 10), # Offset from the point in pixels
                                            textcoords="offset points",
                                            bbox=dict(boxstyle="round,pad=0.5", fc="yellow", ec="k", lw=1, alpha=0.8),
                                            arrowprops=dict(arrowstyle="wedge,tail_width=0.7", fc="yellow", ec="k", alpha=0.8),
                                            fontsize=10)
        self.canvas.draw_idle()

    def clear_annotation(self, event=None):
        """
        Removes the annotation from the plot if it exists.
        The 'event=None' allows this function to be called by event handlers
        (which pass an event object) or directly (e.g., when plot is redrawn).
        """
        if self.annotation:
            self.annotation.remove()
            self.annotation = None
            self.canvas.draw_idle()


# Main application entry point
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StockChartApp()
    window.show()
    sys.exit(app.exec_())