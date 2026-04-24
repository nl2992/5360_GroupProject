import pandas as pd

import matplotlib.pyplot as plt

df = pd.read_csv("price_plot.csv")

plt.plot(df["close"], label="close")

plt.plot(df["HH"], label="HH")

plt.plot(df["LL"], label="LL")

plt.legend()

plt.show()

eq = pd.read_csv("equity_plot.csv")

plt.figure()

plt.plot(eq["E"], label="Equity")

plt.legend()

plt.show()