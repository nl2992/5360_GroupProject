import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


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


