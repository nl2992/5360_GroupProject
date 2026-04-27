#include<iostream>
#include<fstream>
#include<sstream>
#include<vector>
#include<string>
#include<cmath>
#include<limits>
#include<numeric>
#include<deque>
#include<stdexcept>
#include <iomanip>
#include<algorithm>
#include <omp.h>

using namespace std;

const double NaN = numeric_limits<double>::quiet_NaN();

struct Bar{
    string dateStr;
    string timeStr;
    double numTime;
    double open;
    double high;
    double low;
    double close;
};

struct ResultStats{
    double profit;
    double worstDrawdown;
    double pnlStd;
    double numTrades;
};

struct StrategyRunResult {
    vector<double> E;
    vector<double> DD;
    vector<double> trades;
    vector<double> barPnL;
    vector<int> positionRecord;
};


struct WFConfig {
    int inSampleMonths;

    int outSampleMonths;

    int stepMonths;

};
double toDouble(const string& s){
    return stod(s);
}

double parseDataTimeTonumeric(const string& dateStr, const string& timeStr){
    int y = 0, m= 0, d= 0;
    int hh=0, mm=0, ss=0;

    if(dateStr.find('-') != string::npos){
        char dash1,dash2;
        stringstream ds(dateStr);
        ds>>y>>dash1>>m>>dash2>>d;
    }else if(dateStr.find('/') != string::npos){
        char slash1, slash2;
        stringstream ds(dateStr);
        ds>>m>>slash1>>d>>slash2>>y;
    }else{
        throw runtime_error("Unsupported data format: "+dateStr);   
    }

    int colonCount = static_cast<int>(count(timeStr.begin(),timeStr.end(),':'));

    if (colonCount == 2){
        char c1,c2;
        stringstream ts(timeStr);
        ts>>hh>>c1>>mm>>c2>>ss;
    }else if(colonCount ==1){
        char c1;
        stringstream ts(timeStr);
        ts>>hh>>c1>>mm;
        ss=0;
    }else{
        throw runtime_error("Unsupported time format:"+timeStr);
    }

    double datePart = y*10000+m*100+d;
    double timePart = (hh*3600+mm*60+ss)/86400.0;
    return datePart + timePart;
}




// readcsv

vector<Bar> readCSV(const string& filename){
    vector<Bar> data;
    ifstream file(filename);

    if (!file.is_open()){
        throw runtime_error("Cannot open file:"+filename);
    }

    string line;
    getline(file,line);

    while (getline(file,line)){

        if (line.empty()) continue;

        stringstream ss(line);
        string token;
        vector<string> cols;

        while (getline(ss,token,',')){
            cols.push_back(token);
        }

        if (cols.size()<6) continue;

        Bar b;
        b.dateStr = cols[0];
        b.timeStr = cols[1];
        b.open = toDouble(cols[2]);
        b.high = toDouble(cols[3]);
        b.low = toDouble(cols[4]);
        b.close = toDouble(cols[5]);
        b.numTime = parseDataTimeTonumeric(b.dateStr, b.timeStr);

        data.push_back(b);
    }
    return data;
}

//compute standard deviation
double computeStd(const vector<double>& x, int startIdx, int endIdx){
    if (endIdx<startIdx) return 0.0;

    int n = endIdx - startIdx+1;
    if(n<=1) return 0.0;

    double mean=0.0;
    for (int i = startIdx; i<=endIdx; ++i){
        mean += x[i];   
    }

    mean /= static_cast<double>(n);

    double var = 0.0;
    for(int i = startIdx; i<= endIdx; ++i){
        double diff = x[i]-mean;
        var += diff*diff;
    }
    var /= static_cast<double>(n-1);

    return sqrt(var);
    
}

//the function return first index and last index of our trading window
int firstIndexGE(const vector<Bar>& d, double target) {

    for (int i = 0; i < static_cast<int>(d.size()); ++i) {

        if (d[i].numTime >= target) {

            return i;

        }

    }

    return static_cast<int>(d.size()) - 1;

}


//last index of out trading window
int lastIndexLT(const vector<Bar> &d, double target){
    int idx = -1;
    for (int i = 0;i<static_cast<int>(d.size()); ++i){
        if (d[i].numTime<target){
            idx = i;
        }else{
            break;
        }
    }
    return max(0,idx);
}

//result metrics
ResultStats computeStats(
    const vector<double>& E,
    const vector<double>& DD,
    const vector<double>& trades,
    int ind1,
    int ind2,
    int barsBack
){
    vector<double>pnl(E.size(),0.0);

    for (int i=barsBack+1; i<static_cast<int>(E.size());++i){
        pnl[i]=E[i]-E[i-1];
    }

    double worstDD = DD[ind1];
    double totalTrades = 0.0;

    for(int i = ind1;i<=ind2;++i){
        worstDD = min(worstDD,DD[i]);
        totalTrades += trades[i];
    }

    ResultStats res;
    res.profit = E[ind2]-E[ind1];
    res.worstDrawdown=worstDD;
    res.pnlStd = computeStd(pnl,ind1,ind2);
    res.numTrades = totalTrades;

    return res;
}

//compute HH and LL
void computeHHLL(
    const vector<Bar>& d,
    int L,
    int endIdx,
    vector<double>& HH,
    vector<double>& LL
){
    int N = static_cast<int>(d.size());

    HH.assign(N, 0.0);
    LL.assign(N, 0.0);

    deque<int> maxQ;
    deque<int> minQ;

    int warmup = L;

    for (int k = warmup; k <= endIdx; ++k) {

        int newIdx = k - 1;
        int leftIdx = k - L;

        while (!maxQ.empty() && d[maxQ.back()].high <= d[newIdx].high) {
            maxQ.pop_back();
        }

        maxQ.push_back(newIdx);

        while (!maxQ.empty() && maxQ.front() < leftIdx) {
            maxQ.pop_front();
        }

        while (!minQ.empty() && d[minQ.back()].low >= d[newIdx].low) {
            minQ.pop_back();
        }

        minQ.push_back(newIdx);

        while (!minQ.empty() && minQ.front() < leftIdx) {
            minQ.pop_front();
        }

        HH[k] = d[maxQ.front()].high;
        LL[k] = d[minQ.front()].low;
    }
}


ResultStats runStrategyStatsOnly(
    const vector<Bar>& d,
    const vector<double>& HH,
    const vector<double>& LL,
    int startIdx,
    int statStartIdx,
    int statEndIdx,
    int endIdx,
    double S,
    double PV,
    double slpg,
    double E0
){
    int position = 0;

    double benchmarkLong = NaN;
    double benchmarkShort = NaN;

    double E = E0;
    double prevE = E0;

    double EmaxStat = E0;
    double worstDD = 0.0;
    double totalTrades = 0.0;

    vector<double> pnlWindow;
    pnlWindow.reserve(max(0, statEndIdx - statStartIdx + 1));

    double E_at_stat_start = E0;
    double E_at_stat_end = E0;

    bool capturedStartEquity = false;
    bool capturedEndEquity = false;

    for (int k = startIdx; k <= endIdx; ++k) {

        bool traded = false;
        double delta = 0.0;

        if (k > startIdx) {
            delta = PV * (d[k].close - d[k - 1].close) * position;
        }

        if (position == 0) {

            bool buy = d[k].high >= HH[k];
            bool sell = d[k].low <= LL[k];

            if (buy && sell) {

                delta = -slpg + PV * (LL[k] - HH[k]);

                if (k >= statStartIdx && k <= statEndIdx) {
                    totalTrades += 1.0;
                }

            } else {

                if (buy) {

                    delta = -slpg / 2.0 + PV * (d[k].close - HH[k]);
                    position = 1;
                    traded = true;
                    benchmarkLong = d[k].high;

                    if (k >= statStartIdx && k <= statEndIdx) {
                        totalTrades += 0.5;
                    }
                }

                if (sell) {

                    delta = -slpg / 2.0 - PV * (d[k].close - LL[k]);
                    position = -1;
                    traded = true;
                    benchmarkShort = d[k].low;

                    if (k >= statStartIdx && k <= statEndIdx) {
                        totalTrades += 0.5;
                    }
                }
            }
        }

        if (position == 1 && !traded) {

            bool sellShort = d[k].low <= LL[k];
            bool sell = d[k].low <= benchmarkLong * (1.0 - S);

            if (sellShort && sell) {

                delta = delta - slpg - 2.0 * PV * (d[k].close - LL[k]);
                position = -1;
                benchmarkShort = d[k].low;

                if (k >= statStartIdx && k <= statEndIdx) {
                    totalTrades += 1.0;
                }

            } else {

                if (sell) {

                    delta = delta - slpg / 2.0
                          - PV * (d[k].close - benchmarkLong * (1.0 - S));

                    position = 0;

                    if (k >= statStartIdx && k <= statEndIdx) {
                        totalTrades += 0.5;
                    }
                }

                if (sellShort) {

                    delta = delta - slpg - 2.0 * PV * (d[k].close - LL[k]);
                    position = -1;
                    benchmarkShort = d[k].low;

                    if (k >= statStartIdx && k <= statEndIdx) {
                        totalTrades += 1.0;
                    }
                }
            }

            benchmarkLong = max(d[k].high, benchmarkLong);
        }

        if (position == -1 && !traded) {

            bool buyLong = d[k].high >= HH[k];
            bool buy = d[k].high >= benchmarkShort * (1.0 + S);

            if (buyLong && buy) {

                delta = delta - slpg + 2.0 * PV * (d[k].close - HH[k]);
                position = 1;
                benchmarkLong = d[k].high;

                if (k >= statStartIdx && k <= statEndIdx) {
                    totalTrades += 1.0;
                }

            } else {

                if (buy) {

                    delta = delta - slpg / 2.0
                          + PV * (d[k].close - benchmarkShort * (1.0 + S));

                    position = 0;

                    if (k >= statStartIdx && k <= statEndIdx) {
                        totalTrades += 0.5;
                    }
                }

                if (buyLong) {

                    delta = delta - slpg + 2.0 * PV * (d[k].close - HH[k]);
                    position = 1;
                    benchmarkLong = d[k].high;

                    if (k >= statStartIdx && k <= statEndIdx) {
                        totalTrades += 1.0;
                    }
                }
            }

            benchmarkShort = min(d[k].low, benchmarkShort);
        }

        prevE = E;
        E += delta;

        if (k == statStartIdx) {
            E_at_stat_start = prevE;
            EmaxStat = prevE;
            capturedStartEquity = true;
        }

        if (k >= statStartIdx && k <= statEndIdx) {
            EmaxStat = max(EmaxStat, E);
            double dd = E - EmaxStat;
            worstDD = min(worstDD, dd);
            pnlWindow.push_back(E - prevE);
        }

        if (k == statEndIdx) {
            E_at_stat_end = E;
            capturedEndEquity = true;
        }
    }

    ResultStats res;

    if (!capturedStartEquity) {
        E_at_stat_start = E0;
    }

    if (!capturedEndEquity) {
        E_at_stat_end = E;
    }

    res.profit = E_at_stat_end - E_at_stat_start;
    res.worstDrawdown = worstDD;
    res.pnlStd = computeStd(pnlWindow, 0, static_cast<int>(pnlWindow.size()) - 1);
    res.numTrades = totalTrades;

    return res;
}

//run strategy
StrategyRunResult runStrategy(
    const vector<Bar>& d,
    const vector<double>& HH,
    const vector<double>& LL,
    int startIdx,
    int endIdx,
    double S,
    double PV,
    double slpg,
    double E0
){
    int N = static_cast<int>(d.size());

    StrategyRunResult res;

    res.E.assign(N, E0);
    res.DD.assign(N, 0.0);
    res.trades.assign(N, 0.0);
    res.barPnL.assign(N, 0.0);
    res.positionRecord.assign(N, 0);

    int position = 0;

    double benchmarkLong = NaN;
    double benchmarkShort = NaN;

    double Emax = E0;

    for (int k = startIdx; k <= endIdx; ++k) {

        bool traded = false;

        double delta = 0.0;

        if (k > startIdx) {

            delta = PV * (d[k].close - d[k - 1].close) * position;

        }

        // ----------------------------

        // Flat position

        // ----------------------------

        if (position == 0) {

            bool buy = d[k].high >= HH[k];

            bool sell = d[k].low <= LL[k];

            if (buy && sell) {

                // Conservative whipsaw assumption

                delta = -slpg + PV * (LL[k] - HH[k]);

                res.trades[k] = 1.0;

            } else {

                if (buy) {

                    delta = -slpg / 2.0 + PV * (d[k].close - HH[k]);

                    position = 1;

                    traded = true;

                    benchmarkLong = d[k].high;

                    res.trades[k] = 0.5;

                }

                if (sell) {

                    delta = -slpg / 2.0 - PV * (d[k].close - LL[k]);

                    position = -1;

                    traded = true;

                    benchmarkShort = d[k].low;

                    res.trades[k] = 0.5;

                }

            }

        }

        // ----------------------------

        // Long position

        // ----------------------------

        if (position == 1 && !traded) {

            bool sellShort = d[k].low <= LL[k];

            bool sell = d[k].low <= benchmarkLong * (1.0 - S);

            if (sellShort && sell) {

                delta = delta - slpg

                      - 2.0 * PV * (d[k].close - LL[k]);

                position = -1;

                benchmarkShort = d[k].low;

                res.trades[k] = 1.0;

            } else {

                if (sell) {

                    delta = delta - slpg / 2.0

                          - PV * (d[k].close - benchmarkLong * (1.0 - S));

                    position = 0;

                    res.trades[k] = 0.5;

                }

                if (sellShort) {

                    delta = delta - slpg

                          - 2.0 * PV * (d[k].close - LL[k]);

                    position = -1;

                    benchmarkShort = d[k].low;

                    res.trades[k] = 1.0;

                }

            }

            benchmarkLong = max(d[k].high, benchmarkLong);

        }

        // ----------------------------

        // Short position

        // ----------------------------

        if (position == -1 && !traded) {

            bool buyLong = d[k].high >= HH[k];

            bool buy = d[k].high >= benchmarkShort * (1.0 + S);

            if (buyLong && buy) {

                delta = delta - slpg

                      + 2.0 * PV * (d[k].close - HH[k]);

                position = 1;

                benchmarkLong = d[k].high;

                res.trades[k] = 1.0;

            } else {

                if (buy) {

                    delta = delta - slpg / 2.0

                          + PV * (d[k].close - benchmarkShort * (1.0 + S));

                    position = 0;

                    res.trades[k] = 0.5;

                }

                if (buyLong) {

                    delta = delta - slpg

                          + 2.0 * PV * (d[k].close - HH[k]);

                    position = 1;

                    benchmarkLong = d[k].high;

                    res.trades[k] = 1.0;

                }

            }

            benchmarkShort = min(d[k].low, benchmarkShort);

        }

        res.E[k] = (k > startIdx ? res.E[k - 1] : E0) + delta;

        Emax = max(Emax, res.E[k]);

        res.DD[k] = res.E[k] - Emax;

        res.barPnL[k] = delta;

        res.positionRecord[k] = position;
    }

    return res;
}

//generate two csv files
void writePriceCSV(
    const string& filename,
    const vector<Bar> &d,
    const vector<double> &HH,
    const vector<double> &LL,
    const vector<double> &trades,
    int startIdx,
    int endIdx
){
    ofstream out(filename);
    if(! out.is_open()){
        throw runtime_error("cannot open output file" + filename);
    }
    out << "date,time,numTime,close,HH,LL,trades\n";
    
    for (int i = startIdx; i <= endIdx; ++i) {
        out << d[i].dateStr << ","
            << d[i].timeStr << ","
            << d[i].numTime << ","
            <<d[i].close<<","
            <<HH[i]<<","
            <<LL[i]<<","
            <<trades[i]<<"\n";

    }
}

void writeEquityCSV(
    const string& filename,
    const vector<Bar>& d,
    const vector<double>&E,
    int startIdx,
    int endIdx
){
    ofstream out(filename);
    if(!out.is_open()){
        throw runtime_error("Cannot open output file" + filename);

    }

    out << "date,time,numTime,E\n";

    for (int i = startIdx; i <= endIdx; ++i){
        out<<d[i].dateStr<<","
            <<d[i].timeStr<<","
            <<d[i].numTime<<","
            <<E[i]<<"\n";

    }
}

//Walking forward functions
string addMonthsDate(const string& dateStr, int monthsToAdd) {
    int y = 0, m = 0, d = 0;

    if (dateStr.find('-') != string::npos) {
        char dash1, dash2;
        stringstream ss(dateStr);
        ss >> y >> dash1 >> m >> dash2 >> d;
    } else if (dateStr.find('/') != string::npos) {
        char slash1, slash2;
        stringstream ss(dateStr);
        ss >> m >> slash1 >> d >> slash2 >> y;
    } else {
        throw runtime_error("Unsupported date format: " + dateStr);
    }

    m += monthsToAdd;

    while (m > 12) {
        m -= 12;
        y += 1;
    }

    while (m <= 0) {
        m += 12;
        y -= 1;
    }

    stringstream out;
    out << setw(2) << setfill('0') << m << "/"
        << setw(2) << setfill('0') << d << "/"
        << y;

    return out.str();
}


void runWalkForward(
    const vector<Bar>& d,
    const vector<int>& Length,
    const vector<double>& StopPct,
    int inSampleMonths,
    int outSampleMonths,
    int stepMonths,
    double PV,
    double slpg,
    double E0
){
    int N = static_cast<int>(d.size());

    string globalStartDate = d.front().dateStr;
    string globalEndDate = d.back().dateStr;

    string tag = "IS" + to_string(inSampleMonths)
               + "_OOS" + to_string(outSampleMonths)
               + "_STEP" + to_string(stepMonths);

    cout << "\n==================================================" << endl;
    cout << "Running walk-forward: " << tag << endl;
    cout << "==================================================" << endl;

    ofstream resultOut("walk_forward_quarterly_summary_" + tag + ".csv");

    if (!resultOut.is_open()) {
        throw runtime_error("Cannot open result output file.");
    }

    resultOut << "InStart,InEnd,OutStart,OutEnd,"
              << "BestLength,BestStopPct,"
              << "InProfit,InWorstDD,InStd,InTrades,"
              << "OutProfit,OutWorstDD,OutStd,OutTrades\n";

    ofstream oosEquityOut("walk_forward_oos_equity_curve_" + tag + ".csv");

    if (!oosEquityOut.is_open()) {
        throw runtime_error("Cannot open OOS equity output file.");
    }

    oosEquityOut << "date,time,numTime,"
                 << "InStart,InEnd,OutStart,OutEnd,"
                 << "BestLength,BestStopPct,"
                 << "position,barPnL,oosEquity,tradeSize\n";

    ofstream oosTradeOut("walk_forward_oos_trade_events_" + tag + ".csv");

    if (!oosTradeOut.is_open()) {
        throw runtime_error("Cannot open OOS trade output file.");
    }

    oosTradeOut << "date,time,numTime,"
                << "InStart,InEnd,OutStart,OutEnd,"
                << "BestLength,BestStopPct,"
                << "position,tradeSize,barPnL,oosEquity\n";

    ofstream isEquityOut("walk_forward_is_equity_curve_" + tag+ ".csv");
    if (! isEquityOut.is_open()){
        throw runtime_error("Cannot open IS equity output file.");
    }

    isEquityOut << "date,time,numTime,"
                << "InStart,InEnd,OutStart,OutEnd,"
                << "BestLength,BestStopPct,"
                << "position,barPnL,isEquity,tradeSize\n";


    double fullOosEquity = E0;

    string inStartDate = globalStartDate;

    // ----------------------------

    // Walk-forward loop

    // ----------------------------

    while (true) {

        string inEndDate = addMonthsDate(inStartDate, inSampleMonths);

        string outStartDate = inEndDate;

        string outEndDate = addMonthsDate(outStartDate, outSampleMonths);

        double globalEndNum = parseDataTimeTonumeric(globalEndDate, "00:00:00");

        double outEndNum = parseDataTimeTonumeric(outEndDate, "00:00:00");

        if (outEndNum > globalEndNum) {

            break;

        }

        double inSampleStart = parseDataTimeTonumeric(inStartDate, "00:00:00");

        double inSampleEnd = parseDataTimeTonumeric(inEndDate, "00:00:00");

        double outSampleStart = parseDataTimeTonumeric(outStartDate, "00:00:00");

        double outSampleEnd = parseDataTimeTonumeric(outEndDate, "00:00:00");

        int indInSample1Raw = firstIndexGE(d, inSampleStart);

        int indInSample2Raw = lastIndexLT(d, inSampleEnd);

        int indOutSample1Raw = firstIndexGE(d, outSampleStart);

        int indOutSample2Raw = lastIndexLT(d, outSampleEnd);

        if (indInSample1Raw < 0 || indInSample2Raw < 0 ||

            indOutSample1Raw < 0 || indOutSample2Raw < 0) {

            inStartDate = addMonthsDate(inStartDate, stepMonths);

            continue;

        }

        cout << "\nWindow: "

             << inStartDate << " to " << inEndDate

             << " | OOS: "

             << outStartDate << " to " << outEndDate

             << endl;

        // Global best for this walk-forward window

        double bestScore = -1e100;

        int bestL = -1;

        double bestS = 0.0;

        ResultStats bestInRes{};

        ResultStats bestOutRes{};

        // ============================================================

        // Parallel search over Length

        // ============================================================

        #pragma omp parallel

        {

            double localBestScore = -1e100;

            int localBestL = -1;

            double localBestS = 0.0;

            ResultStats localBestInRes{};

            ResultStats localBestOutRes{};

            #pragma omp for schedule(dynamic)

            for (int i = 0; i < static_cast<int>(Length.size()); ++i) {

                int L = Length[i];

                int warmup = L;

                int indInSample1 = max(indInSample1Raw, warmup);

                int indInSample2 = indInSample2Raw;

                int indOutSample1 = max(indOutSample1Raw, warmup);

                int indOutSample2 = indOutSample2Raw;

                if (indInSample1 > indInSample2 || indOutSample1 > indOutSample2) {

                    continue;

                }

                // ----------------------------

                // Compute HH / LL for this Length

                // ----------------------------

                vector<double> HH;

                vector<double> LL;

                computeHHLL(d, L, indOutSample2, HH, LL);

                // ----------------------------

                // Loop over StopPct

                // ----------------------------

                for (int j = 0; j < static_cast<int>(StopPct.size()); ++j) {

                    double S = StopPct[j];

                    // ----------------------------

                    // Run strategy on current WF window

                    // ----------------------------

                    ResultStats inRes = runStrategyStatsOnly(
                        d,
                        HH,
                        LL,
                        indInSample1,
                        indInSample1,
                        indInSample2,
                        indInSample2,
                        S,
                        PV,
                        slpg,
                        E0
                    );

                    double score = inRes.profit;

                    if (score > localBestScore) {

                        ResultStats outRes = runStrategyStatsOnly(
                            d,
                            HH,
                            LL,
                            indInSample1,
                            indOutSample1,
                            indOutSample2,
                            indOutSample2,
                            S,
                            PV,
                            slpg,
                            E0
                        );

                        localBestScore = score;

                        localBestL = L;

                        localBestS = S;

                        localBestInRes = inRes;

                        localBestOutRes = outRes;

                    }

                }

            }

            // Merge thread-local best into global best

            #pragma omp critical

            {

                if (localBestScore > bestScore) {

                    bestScore = localBestScore;

                    bestL = localBestL;

                    bestS = localBestS;

                    bestInRes = localBestInRes;

                    bestOutRes = localBestOutRes;

                }

            }

        }

        if (bestL == -1) {

            cout << "No valid parameter found for this window." << endl;

            inStartDate = addMonthsDate(inStartDate, stepMonths);

            continue;

        }

        // ----------------------------

        // Re-run best strategy and record OOS only

        // ----------------------------

        int bestWarmup = bestL;

        int bestInSample1 = max(indInSample1Raw, bestWarmup);

        int bestOutSample1 = max(indOutSample1Raw, bestWarmup);

        int bestOutSample2 = indOutSample2Raw;

        vector<double> bestHH;

        vector<double> bestLL;

        computeHHLL(d, bestL, bestOutSample2, bestHH, bestLL);

        StrategyRunResult bestRun = runStrategy(
            d,
            bestHH,
            bestLL,
            bestInSample1,
            bestOutSample2,
            bestS,
            PV,
            slpg,
            E0
        );

        // save IS data
        for(int k = bestInSample1; k <= indInSample2Raw; ++k){
            isEquityOut << d[k].dateStr << ","
                        << d[k].timeStr << ","
                        << d[k].numTime << ","
                        << inStartDate << ","
                        << inEndDate << ","
                        << outStartDate << ","
                        << outEndDate << ","
                        << bestL << ","
                        << bestS << ","
                        << bestRun.positionRecord[k] << ","
                        << bestRun.barPnL[k] << ","
                        << bestRun.E[k] << ","
                        << bestRun.trades[k]
                        << "\n";

        }


        for (int k = bestOutSample1; k <= bestOutSample2; ++k) {

            fullOosEquity += bestRun.barPnL[k];

            oosEquityOut << d[k].dateStr << ","
                         << d[k].timeStr << ","
                         << d[k].numTime << ","
                         << inStartDate << ","
                         << inEndDate << ","
                         << outStartDate << ","
                         << outEndDate << ","
                         << bestL << ","
                         << bestS << ","
                         << bestRun.positionRecord[k] << ","
                         << bestRun.barPnL[k] << ","
                         << fullOosEquity << ","
                         << bestRun.trades[k]
                         << "\n";

            if (bestRun.trades[k] > 0.0) {

                oosTradeOut << d[k].dateStr << ","
                            << d[k].timeStr << ","
                            << d[k].numTime << ","
                            << inStartDate << ","
                            << inEndDate << ","
                            << outStartDate << ","
                            << outEndDate << ","
                            << bestL << ","
                            << bestS << ","
                            << bestRun.positionRecord[k] << ","
                            << bestRun.trades[k] << ","
                            << bestRun.barPnL[k] << ","
                            << fullOosEquity
                            << "\n";

            }

        }

        resultOut << inStartDate << ","

                  << inEndDate << ","

                  << outStartDate << ","

                  << outEndDate << ","

                  << bestL << ","

                  << bestS << ","

                  << bestInRes.profit << ","

                  << bestInRes.worstDrawdown << ","

                  << bestInRes.pnlStd << ","

                  << bestInRes.numTrades << ","

                  << bestOutRes.profit << ","

                  << bestOutRes.worstDrawdown << ","

                  << bestOutRes.pnlStd << ","

                  << bestOutRes.numTrades

                  << "\n";

        cout << "Best for window: "

             << "L = " << bestL

             << ", S = " << bestS

             << " | InProfit = " << bestInRes.profit

             << " | OutProfit = " << bestOutRes.profit

             << endl;

        inStartDate = addMonthsDate(inStartDate, stepMonths);

    }

    resultOut.close();
    oosEquityOut.close();
    oosTradeOut.close();
    isEquityOut.close();

    cout << "\nFinished: " << tag << endl;
    cout << "Quarterly summary saved to walk_forward_quarterly_summary_" << tag << ".csv" << endl;
    cout << "OOS equity curve saved to walk_forward_oos_equity_curve_" << tag << ".csv" << endl;
    cout << "OOS trade events saved to walk_forward_oos_trade_events_" << tag << ".csv" << endl;
    cout << "IS equity curve saved to walk_forward_is_equity_curve_" << tag << ".csv" << endl;
}



int main() {

    try {

        string dataFile = "TY-5minHLV.csv";

        double slpg = 19;
        double PV = 1000;
        double E0 = 100000.0;
        // ----------------------------
        // Parameter grid
        // ----------------------------
        vector<int> Length;
        for (int L = 500; L <= 10000; L += 100) {
            Length.push_back(L);
        }
        vector<double> StopPct;
        for (int i = 10; i <= 100; i += 10) {
            StopPct.push_back(i / 1000.0);
        }
        // ----------------------------
        // Load data
        // ----------------------------
        vector<Bar> d = readCSV(dataFile);
        int N = static_cast<int>(d.size());
        cout << "Loaded bars: " << N << endl;
        if (N == 0) {
            throw runtime_error("No data loaded.");
        }
        cout << "OpenMP max threads: " << omp_get_max_threads() << endl;
        vector<WFConfig> configs = {            
            
            {48,12,12},
  

        };
        for (const auto& cfg : configs) {

            runWalkForward(
                d,
                Length,
                StopPct,
                cfg.inSampleMonths,
                cfg.outSampleMonths,
                cfg.stepMonths,
                PV,
                slpg,
                E0
            );

        }

        cout << "\nAll walk-forward configurations finished." << endl;

    } catch (const exception& e) {

        cerr << "Error: " << e.what() << endl;

    }

    return 0;

}