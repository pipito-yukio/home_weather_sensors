import argparse
import os
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox, filedialog
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import pandas as pd
import util.file_util as FU
from util.date_util import add_day_string
from log import logsetting

"""
気象データプロットアプリ(GUI) with TKinter
[実行方法]
1 CSVファイルを指定して実行
 (例) --csv-path ~/Downloads/csv/weather_esp8266_1_all_20211108.csv
2 引数なしで実行しファイルメニューの[Open CSV]からファイルを開く
"""


base_dir = os.path.abspath(os.path.dirname(__file__))
save_imagename = FU.gen_imgname(__file__)
save_filename = os.path.join(base_dir, "images", save_imagename)

# Constant
LBL_FONT_SIZE, TICK_LBL_FONT_SIZE, TICK_LBL_DATE_FONT_SIZE = 10, 8, 7
# Tkinter default options
FRAME_KWARGS, FRAME_PACK_KWARGS = {"relief": "ridge"}, {"padx": 10, "padx": 10}
WIDGET_PAD_KWARGS = {"padx": 5, "pady": 4, "ipadx": 2, "ipady": 2}

# Global Config
app_conf, plot_conf = None, None

log_conf_path = os.path.join(base_dir, "conf")
app_logs_path = os.path.join(base_dir, "logs")
logger = logsetting.create_logger("main_app", log_conf_path, os.environ.get("APP_LOGS_PATH", app_logs_path))


def load_csv(file):
    # Load weather DataFrame
    df = pd.read_csv(file,
                     parse_dates=['measurement_time'],
                     usecols=['measurement_time', 'temp_out', 'temp_in', 'humid', 'pressure'])
    return df


class PlotGraph(tk.Frame):
    def __init__(self, parent, dataset, fig_size, **kwargs):
        super().__init__(master=parent, **kwargs)
        self.dataset = dataset
        fig, (axes_temp, axes_humid, axes_pressure) = plt.subplots(3, 1,
                                                                   figsize=fig_size,
                                                                   tight_layout=True,
                                                                   sharex=True)
        self.figure = fig
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.X, expand=1)
        self.axes_temp = axes_temp
        self.axes_humid = axes_humid
        self.axes_pressure = axes_pressure
        self.dataset = None

    def set_dataset(self, dataset):
        self.dataset = dataset

    def set_axes_temp(self):
        plt.setp(self.axes_temp.get_yticklabels(), fontsize=TICK_LBL_FONT_SIZE)
        self.axes_temp.set_ylim(plot_conf["ylim"]["temp"])
        self.axes_temp.set_ylabel('気温 (℃)', fontsize=LBL_FONT_SIZE)
        self.axes_temp.set_title("気象データ")
        self.axes_temp.grid()

    def set_axes_humid(self):
        plt.setp(self.axes_humid.get_yticklabels(), fontsize=TICK_LBL_FONT_SIZE)
        self.axes_humid.set_ylim([0, 100])
        self.axes_humid.set_ylabel('室内湿度 (％)', fontsize=LBL_FONT_SIZE)
        self.axes_humid.grid()

    def set_axes_pressure(self):
        # mesurement_time
        plt.setp(self.axes_pressure.get_xticklabels(),
                 rotation=30, horizontalalignment='right', rotation_mode='anchor', fontsize=TICK_LBL_DATE_FONT_SIZE)
        plt.setp(self.axes_pressure.get_yticklabels(), fontsize=TICK_LBL_FONT_SIZE)
        # xtick label interval 1day
        self.axes_pressure.xaxis.set_major_locator(mdates.DayLocator(interval=1, tz=None))
        # xtick label format: yyyy/mm/dd
        self.axes_pressure.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m/%d'))
        self.axes_pressure.set_ylim(plot_conf["ylim"]["pressure"])
        self.axes_pressure.set_ylabel('気圧 (hPa)', fontsize=LBL_FONT_SIZE)
        self.axes_pressure.grid()

    def plot_range(self, plot_from, plot_to):
        plot_add_1_to = add_day_string(plot_to)
        logger.debug("plot_from: {}, plot_add_1_to: {}".format(plot_from, plot_add_1_to))
        plt_range = (self.dataset['measurement_time'] >= plot_from) & (self.dataset['measurement_time'] < plot_add_1_to)
        plt_dataset = self.dataset.loc[plt_range]
        self.axes_temp.clear()
        self.set_axes_temp()
        self.axes_temp.plot(plt_dataset['measurement_time'], plt_dataset['temp_out'],
                            color='blue', marker='', label='外気温')
        self.axes_temp.plot(plt_dataset['measurement_time'], plt_dataset['temp_in'],
                            color='red', marker='', label='室内気温')
        # legent setting this place
        self.axes_temp.legend(loc='lower right')

        self.axes_humid.clear()
        self.set_axes_humid()
        self.axes_humid.plot(plt_dataset['measurement_time'], plt_dataset['humid'], color='green', marker='')

        self.axes_pressure.clear()
        self.set_axes_pressure()
        self.axes_pressure.plot(plt_dataset['measurement_time'], plt_dataset['pressure'], color='fuchsia', marker='')
        # show
        self.canvas.draw()


class MainApp:
    def __init__(self, title, geometory, fig_size):
        self.window = tk.Tk()
        self.window.title(title)
        self.window.geometry(geometory)
        self.window.protocol("WM_DELETE_WINDOW", self.quit)
        self.fig_size = fig_size
        self.dataset = None
        self.days_list = None
        self.frame_graph = None
        self.cboFromDate = None
        self.cboToDate = None
        self.create_widgets()

    def quit(self):
        self.window.quit()
        self.window.destroy()
        exit()

    def save_dialog(self):
        filename = filedialog.asksaveasfilename(
            title='Save filename',
            initialdir=app_conf["saveas"]["initialdir"],
        )
        if filename:
            self.frame_graph.figure.savefig(filename, bbox_inches='tight')
            messagebox.showinfo(
                title='Selected File',
                message=filename
            )

    def open_filedialog(self):
        filename = filedialog.askopenfile(
            title='Open CSV file',
            initialdir=app_conf["openfiles"]["initialdir"],
            filetypes=(('CSV files', '*.csv'), ('CSV files', '*.CSV'), )
        )
        if filename:
            self.open_csv(filename)

    def open_csv(self, csv_file):
        df = load_csv(csv_file)
        df.index = df['measurement_time']
        logger.debug("df.index: {}".format(df.index))

        day_group = df.groupby(
            # by=[df.index.year, df.index.month, plt_temp_subset.index.day],
            by=[df['measurement_time'].dt.date],
        )
        # <class 'pandas.core.groupby.generic.DataFrameGroupBy'>
        logger.debug("type(day_group): {}".format(type(day_group)))
        # type(measurement_dates): <class 'pandas.core.series.Series'>
        measurement_dates = day_group['measurement_time'].count()
        measurement_dates.index.set_names(["measurement_date"], inplace=True)
        logger.debug("type(measurement_dates): {}".format(type(measurement_dates)))
        # dates_idx: Index([2021-10-01, 2021-10-02,..., 2021-10-08], dtype='object', name='measurement_date')
        dates_idx = measurement_dates.index
        # days_list=[datetime.date(2021, 10, 1), ..., datetime.date(2021, 10, 8)]
        days_list = [dt.strftime('%Y-%m-%d') for dt in dates_idx.to_list()]
        self.dataset = df
        self.frame_graph.set_dataset(self.dataset)
        self.days_list = days_list
        # Initial plot 7 days.
        idx_to_date = 6 if len(self.days_list) > 6 else len(self.days_list) - 1
        logger.debug("dates_idx: {}".format(dates_idx))
        logger.debug("days_list: {}".format(days_list))
        logger.debug("idx_to_date: {}".format(idx_to_date))
        self.cboFromDate["values"] = self.cboToDate["values"] = self.days_list
        self.cboFromDate.current(0)
        self.cboToDate.current(idx_to_date)
        # 初期表示
        self.plot_range(self.days_list[0], self.days_list[idx_to_date])

    def create_widgets(self):
        plotMainFrame = tk.LabelFrame(master=self.window, text="気象データグラフ", **FRAME_KWARGS)
        self.frame_graph = PlotGraph(plotMainFrame, self.dataset, self.fig_size)
        self.frame_graph.pack(side=tk.TOP, fill=tk.X, expand=1, **FRAME_PACK_KWARGS)
        plotMainFrame.pack(side=tk.TOP, fill=tk.X, expand=1, **FRAME_PACK_KWARGS)

        opeFrame = tk.LabelFrame(self.window, text="操作：")
        lblFromDate = tk.Label(opeFrame, text="開始日付:", bg="cyan")
        lblFromDate.pack(side=tk.LEFT, **WIDGET_PAD_KWARGS)
        cboFromDate = ttk.Combobox(opeFrame, width=12, justify=tk.CENTER)
        cboFromDate.pack(side=tk.LEFT, **WIDGET_PAD_KWARGS)
        lblToDate = tk.Label(opeFrame, text="終了日付:", bg="cyan")
        lblToDate.pack(side=tk.LEFT, **WIDGET_PAD_KWARGS)
        cboToDate = ttk.Combobox(opeFrame, width=12, justify=tk.CENTER)
        cboToDate.pack(side=tk.LEFT, **WIDGET_PAD_KWARGS)

        btnPlot = tk.Button(opeFrame, text="表示", command=self.make_graph)
        btnPlot.pack(side=tk.LEFT, **WIDGET_PAD_KWARGS)
        btnSave = tk.Button(opeFrame, text="保存", command=self.save_dialog)
        btnSave.pack(side=tk.LEFT, **WIDGET_PAD_KWARGS)
        opeFrame.pack(side=tk.BOTTOM, fill=tk.X, expand=1, **FRAME_PACK_KWARGS)
        self.cboFromDate = cboFromDate
        self.cboToDate = cboToDate

        # Menu bar
        menu_bar = tk.Menu(plotMainFrame)
        self.window.config(menu=menu_bar)
        # Add Menu items
        menu_file = tk.Menu(menu_bar, tearoff=0)
        menu_file.add_command(label="Open CSV", command=self.open_filedialog)
        menu_file.add_command(label="Exit", command=self.quit)
        menu_bar.add_cascade(label="File", menu=menu_file)

    def plot_range(self, from_date, to_date):
        self.frame_graph.plot_range(from_date, to_date)

    def make_graph(self):
        from_date, to_date = self.cboFromDate.get(), self.cboToDate.get()
        self.plot_range(from_date, to_date)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-path", type=str, help="Weather csv file path.")
    args = parser.parse_args()

    # Load plot configuration
    app_conf = FU.read_json(os.path.join(base_dir, "conf", "app_weather.json"))
    logger.info("app_conf: {}".format(app_conf))
    plot_conf = app_conf["plot"]
    # Tkinterのグラフに日本語フォント表示
    # コマンドラインから実行する場合は、カレントのmatplotrcが適用されるが、Tkinterウインドウ内では日本語が文字化けする
    plt.rcParams['font.family'] = ['sans-serif']

    app = MainApp("気象データプロットアプリ", geometory=app_conf["geometory"], fig_size=plot_conf["figsize"])
    # CSVファイルを指定された場合は、指定されたファイルを開いてグラフを表示する
    if args.csv_path is not None:
        csv_file = os.path.expanduser(args.csv_path)
        if os.path.exists(csv_file):
            app.open_csv(csv_file)
    app.window.mainloop()
