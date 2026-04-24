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
#include<algorithm>


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

int main() {
    try {
        string dataFile = "HO-5minHLV.csv";

        int barsBack = 17001;
        double slpg = 47.0;
        double PV = 42000.0;
        double E0 = 100000.0;

        vector<int> Length = {12700};
        vector<double> StopPct = {0.010};

        vector<Bar> d = readCSV(dataFile);
        int N = static_cast<int>(d.size());

        cout << "Loaded bars: " << N << endl;

        // 简化版时间比较
        double inSampleStart  = parseDataTimeTonumeric("01/01/1980", "00:00:00");
        double inSampleEnd    = parseDataTimeTonumeric("01/01/2000", "00:00:00");
        double outSampleStart = parseDataTimeTonumeric("01/01/2000", "00:00:00");
        double outSampleEnd   = parseDataTimeTonumeric("03/23/2023", "00:00:00");

        int indInSample1  = max(firstIndexGE(d, inSampleStart), barsBack);
        int indInSample2  = max(lastIndexLT(d, inSampleEnd + 1.0), barsBack);

        int indOutSample1 = max(firstIndexGE(d, outSampleStart), barsBack);
        int indOutSample2 = max(lastIndexLT(d, outSampleEnd + 1.0), barsBack);

        for (int i = 0; i < static_cast<int>(Length.size()); ++i) {
            int L = Length[i];
            cout << "calculating for Length = " << L << endl;

            if (L <= 0) {
                throw runtime_error("Length must be positive.");
            }
            if (barsBack < L) {
                throw runtime_error("barsBack must be >= L.");
            }

            vector<double> HH(N, 0.0), LL(N, 0.0);

            // -------- O(N) 单调队列计算 HH / LL --------
            deque<int> maxQ;  // high: 单调递减
            deque<int> minQ;  // low : 单调递增

            for (int k = barsBack; k < N; ++k) {
                int newIdx = k - 1;   // 新进入窗口的元素
                int leftIdx = k - L;  // 窗口左边界，窗口是 [k-L, k-1]

                // 更新 maxQ: high 单调递减
                while (!maxQ.empty() && d[maxQ.back()].high <= d[newIdx].high) {
                    maxQ.pop_back();
                }
                maxQ.push_back(newIdx);

                // 删除滑出窗口的元素
                while (!maxQ.empty() && maxQ.front() < leftIdx) {
                    maxQ.pop_front();
                }

                // 更新 minQ: low 单调递增
                while (!minQ.empty() && d[minQ.back()].low >= d[newIdx].low) {
                    minQ.pop_back();
                }
                minQ.push_back(newIdx);

                // 删除滑出窗口的元素
                while (!minQ.empty() && minQ.front() < leftIdx) {
                    minQ.pop_front();
                }

                HH[k] = d[maxQ.front()].high;
                LL[k] = d[minQ.front()].low;
            }

            for (int j = 0; j < static_cast<int>(StopPct.size()); ++j) {
                double S = StopPct[j];

                int position = 0;
                double benchmarkLong = NaN;
                double benchmarkShort = NaN;

                vector<double> E(N, E0);
                vector<double> DD(N, 0.0);
                vector<double> trades(N, 0.0);

                double Emax = E0;

                for (int k = barsBack; k < N; ++k) {
                    bool traded = false;
                    double delta = 0.0;

                    if (k > 0) {
                        delta = PV * (d[k].close - d[k - 1].close) * position;
                    }

                    if (position == 0) {
                        bool buy = d[k].high >= HH[k];
                        bool sell = d[k].low <= LL[k];

                        if (buy && sell) {
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

                    if (position == 1 && !traded) {
                        bool sellShort = d[k].low <= LL[k];
                        bool sell = d[k].low <= (benchmarkLong * (1.0 - S));

                        if (sellShort && sell) {
                            delta = delta - slpg - 2.0 * PV * (d[k].close - LL[k]);
                            position = -1;
                            benchmarkShort = d[k].low;
                            trades[k] = 1.0;
                        } else {
                            if (sell) {
                                delta = delta - slpg / 2.0
                                      - PV * (d[k].close - (benchmarkLong * (1.0 - S)));
                                position = 0;
                                trades[k] = 0.5;
                            }

                            if (sellShort) {
                                delta = delta - slpg - 2.0 * PV * (d[k].close - LL[k]);
                                position = -1;
                                benchmarkShort = d[k].low;
                                trades[k] = 1.0;
                            }
                        }

                        benchmarkLong = max(d[k].high, benchmarkLong);
                    }

                    if (position == -1 && !traded) {
                        bool buyLong = d[k].high >= HH[k];
                        bool buy = d[k].high >= (benchmarkShort * (1.0 + S));

                        if (buyLong && buy) {
                            delta = delta - slpg + 2.0 * PV * (d[k].close - HH[k]);
                            position = 1;
                            benchmarkLong = d[k].high;
                            trades[k] = 1.0;
                        } else {
                            if (buy) {
                                delta = delta - slpg / 2.0
                                      + PV * (d[k].close - (benchmarkShort * (1.0 + S)));
                                position = 0;
                                trades[k] = 0.5;
                            }

                            if (buyLong) {
                                delta = delta - slpg + 2.0 * PV * (d[k].close - HH[k]);
                                position = 1;
                                benchmarkLong = d[k].high;
                                trades[k] = 1.0;
                            }
                        }

                        benchmarkShort = min(d[k].low, benchmarkShort);
                    }

                    E[k] = (k > 0 ? E[k - 1] : E0) + delta;
                    Emax = max(Emax, E[k]);
                    DD[k] = E[k] - Emax;
                }

                ResultStats inRes =
                    computeStats(E, DD, trades, indInSample1, indInSample2, barsBack);

                ResultStats outRes =
                    computeStats(E, DD, trades, indOutSample1, indOutSample2, barsBack);
                writePriceCSV(
                    "price_plot.csv",d,HH,LL,trades,indOutSample1,indOutSample2);
                writeEquityCSV("equity_plot.csv",d,E,indOutSample1,indOutSample2);

                cout << "S = " << S
                     << " | in-sample: "
                     << inRes.profit << ", "
                     << inRes.worstDrawdown << ", "
                     << inRes.pnlStd << ", "
                     << inRes.numTrades
                     << " | out-sample: "
                     << outRes.profit << ", "
                     << outRes.worstDrawdown << ", "
                     << outRes.pnlStd << ", "
                     << outRes.numTrades
                     << endl;
            }
        }
    } catch (const exception& e) {
        cerr << "Error: " << e.what() << endl;
    }

    return 0;
}




