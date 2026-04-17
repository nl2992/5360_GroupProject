import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
TYdata = pd.read_csv("TY-5minHLV.csv")
TYdata["numTime"] = pd.to_datetime(TYdata["Date"].astype(str)+" "+TYdata["Time"].astype(str))
TYdata = TYdata.reset_index(drop=True)
print(TYdata.tail())

p = TYdata["Close"].dropna()
p =p.shift(-1)
print(p)

def push_response_test(price,tau=10,n_bins=50):
    """

    :param price: pandas series of prices
    :param tau: time scale
    :param n_bins: number of bins for push value
    :param trim_q: quantile trimming for extremes
    """

    if tau<=0:
        raise ValueError("tau must be a positive integer.")
    if len(price["Close"])<= 2*tau:
        raise ValueError("Price series is too short for the chose tau")
    p = price["Close"].dropna()

    #current - past tau periods
    dp = p-p.shift(tau)
    push = dp
    dp_response = p.shift(-tau)-p
    response = dp_response

    df = pd.DataFrame({
        "push":push,
        "response":response
    }).dropna()
    df["bin"] = pd.qcut(df["push"],q=n_bins,duplicates="drop")
    grouped = df.groupby("bin",observed=True).agg(
        push_mean=("push","mean"),
        response_mean=("response","mean"),
        count=("response","size")  ,
    ).dropna()
    return grouped

def variance_test(price,q):
    logp = np.log(price["Close"].dropna())

    r1 = logp.diff().dropna()
    rq = logp.diff(q).dropna()

    vr =  np.var(rq,ddof=1)/(q*np.var(r1,ddof=1))
    return vr


if __name__ == "__main__":
    tau_list = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48,

                72, 96, 144, 192, 288, 432, 576,

                864, 1152, 1440, 2016, 2880]

    for i in tau_list:
        push_response = push_response_test(price=TYdata,tau=i)
        plt.figure(figsize=(7,5))
        plt.plot(push_response["push_mean"],push_response["response_mean"])
        plt.axhline(0,linewidth=1)
        plt.axvline(0,linewidth=1)
        plt.xlabel("push")
        plt.ylabel("average response")
        plt.title(f"tau = {i}")
        plt.tight_layout()
        plt.show()

    q_list = np.arange(1,300,1)
    vr_list = []

    for q in q_list:
        vr=variance_test(TYdata,q)
        vr_list.append(vr)
        print(f"q={q:>3}, VR = {vr:.4f}")