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



int main() {

    try {

        string dataFile = "HO-5minHLV.csv";

        double slpg = 47.0;

        double PV = 42000.0;

        double E0 = 100000.0;

        // ----------------------------

        // Parameter grid

        // ----------------------------

        vector<int> Length;

        for (int L = 500; L <= 10000; L += 20) {

            Length.push_back(L);

        }

        vector<double> StopPct;

        for (int i = 5; i <= 100; i += 5) {

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

        string globalStartDate = d.front().dateStr;

        string globalEndDate = d.back().dateStr;

        // ----------------------------

        // Walk-forward setup

        // ----------------------------

        int inSampleMonths = 48;   // 4 years

        int outSampleMonths = 6;   // 6 months

        int stepMonths = 48;       // update every 4 years

        ofstream resultOut("walk_forward_4y_update_results.csv");

        if (!resultOut.is_open()) {

            throw runtime_error("Cannot open result output file.");

        }

        resultOut << "InStart,InEnd,OutStart,OutEnd,"

                  << "BestLength,BestStopPct,"

                  << "InProfit,InWorstDD,InStd,InTrades,"

                  << "OutProfit,OutWorstDD,OutStd,OutTrades\n";

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

                    vector<double> HH(N, 0.0);

                    vector<double> LL(N, 0.0);

                    deque<int> maxQ;

                    deque<int> minQ;

                    for (int k = warmup; k <= indOutSample2; ++k) {

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

                    // ----------------------------

                    // Loop over StopPct

                    // ----------------------------

                    for (int j = 0; j < static_cast<int>(StopPct.size()); ++j) {

                        double S = StopPct[j];

                        int position = 0;

                        double benchmarkLong = NaN;

                        double benchmarkShort = NaN;

                        vector<double> E(N, E0);

                        vector<double> DD(N, 0.0);

                        vector<double> trades(N, 0.0);

                        double Emax = E0;

                        // ----------------------------

                        // Run strategy on current WF window

                        // ----------------------------

                        for (int k = indInSample1; k <= indOutSample2; ++k) {

                            bool traded = false;

                            double delta = 0.0;

                            if (k > indInSample1) {

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

                                    trades[k] = 1.0;

                                } else {

                                    if (buy) {

                                        delta = -slpg / 2.0 + PV * (d[k].close - HH[k]);

                                        position = 1;

                                        traded = true;

                                        benchmarkLong = d[k].high;

                                        trades[k] = 0.5;

                                    }

                                    if (sell) {

                                        delta = -slpg / 2.0 - PV * (d[k].close - LL[k]);

                                        position = -1;

                                        traded = true;

                                        benchmarkShort = d[k].low;

                                        trades[k] = 0.5;

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

                                    trades[k] = 1.0;

                                } else {

                                    if (sell) {

                                        delta = delta - slpg / 2.0

                                              - PV * (d[k].close - benchmarkLong * (1.0 - S));

                                        position = 0;

                                        trades[k] = 0.5;

                                    }

                                    if (sellShort) {

                                        delta = delta - slpg

                                              - 2.0 * PV * (d[k].close - LL[k]);

                                        position = -1;

                                        benchmarkShort = d[k].low;

                                        trades[k] = 1.0;

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

                                    trades[k] = 1.0;

                                } else {

                                    if (buy) {

                                        delta = delta - slpg / 2.0

                                              + PV * (d[k].close - benchmarkShort * (1.0 + S));

                                        position = 0;

                                        trades[k] = 0.5;

                                    }

                                    if (buyLong) {

                                        delta = delta - slpg

                                              + 2.0 * PV * (d[k].close - HH[k]);

                                        position = 1;

                                        benchmarkLong = d[k].high;

                                        trades[k] = 1.0;

                                    }

                                }

                                benchmarkShort = min(d[k].low, benchmarkShort);

                            }

                            E[k] = (k > indInSample1 ? E[k - 1] : E0) + delta;

                            Emax = max(Emax, E[k]);

                            DD[k] = E[k] - Emax;

                        }

                        ResultStats inRes =

                            computeStats(E, DD, trades, indInSample1, indInSample2, warmup);

                        ResultStats outRes =

                            computeStats(E, DD, trades, indOutSample1, indOutSample2, warmup);

                        double score = inRes.profit;

                        if (score > localBestScore) {

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

        cout << "\nFinished. Results saved to walk_forward_4y_update_results.csv" << endl;

    } catch (const exception& e) {

        cerr << "Error: " << e.what() << endl;

    }

    return 0;

}