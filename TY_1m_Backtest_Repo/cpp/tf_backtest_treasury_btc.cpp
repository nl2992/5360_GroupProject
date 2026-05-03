#include <algorithm>
#include <cmath>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

// Standalone C++17 walk-forward backtester for the strict trend-following
// Channel WithDDControl workflow used in the project notebooks.
//
// Default round-turn transaction-cost assumptions:
// - TY:  $18.625 / contract round-turn
//        = the TF Data file's official Slpg for TY.
// - BTC: $25.00 / contract round-turn
//        = the TF Data file's official Slpg for BTC.
//
// These defaults now mirror the assignment spreadsheet directly while still
// exposing CLI overrides if the group wants a later sensitivity study.

namespace fs = std::filesystem;

struct Bar {
    std::string date;
    std::string time;
    std::string datetime;
    double open = 0.0;
    double high = 0.0;
    double low = 0.0;
    double close = 0.0;
    double volume = 0.0;
};

struct MarketSpec {
    std::string ticker;
    std::string name;
    double point_value = 0.0;
    double tick_value = 0.0;
    double round_turn_cost = 0.0;
    double initial_equity = 100000.0;
    bool use_session_filter = false;
    int session_start_min = 0;
    int session_end_min = 24 * 60;
    int session_minutes = 0;
    int bars_per_session = 0;
    int trading_days_per_year = 0;
    int professor_tau = 0;
    int active_bar_minutes = 5;
    int expected_start_key = 0;
    double min_plausible_price = 0.0;
    double professor_stop = 0.02;
    std::vector<int> quick_L;
    std::vector<double> quick_S;
    std::string cost_note;
};

struct TfParams {
    int L = 0;
    double S = 0.0;
};

struct TradeRecord {
    std::string market;
    std::string run_type;
    int period = 0;
    int L = 0;
    double S = 0.0;
    int entry_bar = -1;
    int exit_bar = -1;
    std::string entry_time;
    std::string exit_time;
    int direction = 0;
    double entry_price = 0.0;
    double exit_price = 0.0;
    int duration_bars = 0;
    double gross_pnl = 0.0;
    double transaction_cost = 0.0;
    double net_pnl = 0.0;
    double turnover_contracts = 0.0;
    double turnover_notional = 0.0;
    bool is_oos = false;
};

struct BacktestResult {
    bool error = false;
    std::string why;
    TfParams params;
    int slice_start = 0;
    int eval_start = 0;
    int eval_end = 0;
    int warmup_bars = 0;
    int end_position = 0;
    double gross_profit = 0.0;
    double net_profit = 0.0;
    double gross_max_dd = 0.0;
    double net_max_dd = 0.0;
    double gross_objective = 0.0;
    double net_objective = 0.0;
    int num_closed_trades = 0;
    std::vector<double> gross_equity;
    std::vector<double> net_equity;
    std::vector<double> gross_drawdown;
    std::vector<double> net_drawdown;
    std::vector<int> position;
    std::vector<double> gross_bar_pnl;
    std::vector<double> net_bar_pnl;
    std::vector<double> transaction_cost;
    std::vector<double> turnover_contracts;
    std::vector<double> turnover_notional;
    std::vector<double> trade_units;
    std::vector<TradeRecord> ledger;
};

struct GridSearchResult {
    bool valid = false;
    TfParams best_params;
    BacktestResult best_result;
    int tested = 0;
};

struct PeriodRow {
    int period = 0;
    std::string market;
    std::string is_start;
    std::string is_end;
    std::string oos_start;
    std::string oos_end;
    int L = 0;
    double S = 0.0;
    double is_gross_objective = 0.0;
    double is_net_objective = 0.0;
    double is_gross_profit = 0.0;
    double is_net_profit = 0.0;
    double is_gross_max_dd = 0.0;
    double is_net_max_dd = 0.0;
    double oos_gross_objective = 0.0;
    double oos_net_objective = 0.0;
    double oos_gross_profit = 0.0;
    double oos_net_profit = 0.0;
    double oos_gross_max_dd = 0.0;
    double oos_net_max_dd = 0.0;
    int oos_closed_trades = 0;
    int tested = 0;
};

struct SeriesRow {
    std::string market;
    std::string run_type;
    int period = 0;
    std::string datetime;
    std::string date;
    std::string time;
    int L = 0;
    double S = 0.0;
    double close = 0.0;
    int position = 0;
    int delta_position = 0;
    double gross_bar_pnl = 0.0;
    double transaction_cost = 0.0;
    double net_bar_pnl = 0.0;
    double gross_equity = 0.0;
    double net_equity = 0.0;
    double gross_return = 0.0;
    double net_return = 0.0;
    double turnover_contracts = 0.0;
    double turnover_notional = 0.0;
    double trade_units = 0.0;
    bool is_oos = false;
    std::string segment;
};

struct SummaryRow {
    std::string market;
    std::string run_type;
    std::string start_time;
    std::string end_time;
    int bars = 0;
    int periods = 0;
    int L = 0;
    double S = 0.0;
    double gross_profit = 0.0;
    double net_profit = 0.0;
    double gross_max_dd = 0.0;
    double net_max_dd = 0.0;
    double gross_roa = 0.0;
    double net_roa = 0.0;
    double total_cost = 0.0;
    double turnover_contracts = 0.0;
    double turnover_notional = 0.0;
    int closed_trades = 0;
    double gross_stdev = 0.0;
    double net_stdev = 0.0;
    double trade_units = 0.0;
    int bars_back = 0;
    double round_turn_cost = 0.0;
    std::string cost_note;
};

struct WalkForwardBundle {
    std::vector<PeriodRow> periods;
    std::vector<SeriesRow> oos_rows;
    std::vector<TradeRecord> oos_trades;
};

struct IndexBounds {
    int start_idx = 0;
    int end_exclusive = 0;
};

struct ReferenceRunConfig {
    std::string market;
    std::string is_start;
    std::string is_end;
    std::string oos_start;
    std::string oos_end;
    int bars_back = 17001;
    double split_ratio = 0.70;
    std::string source;
};

struct ReferenceSliceStats {
    int start_idx = 0;
    int end_exclusive = 0;
    double gross_profit = 0.0;
    double net_profit = 0.0;
    double gross_worst_drawdown = 0.0;
    double net_worst_drawdown = 0.0;
    double gross_stdev = 0.0;
    double net_stdev = 0.0;
    double trade_units = 0.0;
    double gross_objective = 0.0;
    double net_objective = 0.0;
};

struct ReferenceSurfaceRow {
    std::string market;
    int L = 0;
    double S = 0.0;
    int bars_back = 0;
    std::string is_start;
    std::string is_end;
    std::string oos_start;
    std::string oos_end;
    double is_gross_profit = 0.0;
    double is_net_profit = 0.0;
    double is_gross_worst_drawdown = 0.0;
    double is_net_worst_drawdown = 0.0;
    double is_gross_stdev = 0.0;
    double is_net_stdev = 0.0;
    double is_trade_units = 0.0;
    double is_gross_objective = 0.0;
    double is_net_objective = 0.0;
    double oos_gross_profit = 0.0;
    double oos_net_profit = 0.0;
    double oos_gross_worst_drawdown = 0.0;
    double oos_net_worst_drawdown = 0.0;
    double oos_gross_stdev = 0.0;
    double oos_net_stdev = 0.0;
    double oos_trade_units = 0.0;
    double oos_gross_objective = 0.0;
    double oos_net_objective = 0.0;
};

struct ReferenceBundle {
    ReferenceRunConfig config;
    IndexBounds is_bounds;
    IndexBounds oos_bounds;
    std::vector<ReferenceSurfaceRow> surface;
    TfParams best_params;
    BacktestResult best_result;
    ReferenceSliceStats is_stats;
    ReferenceSliceStats oos_stats;
    std::vector<SeriesRow> series_rows;
    std::vector<TradeRecord> trades;
    std::vector<SummaryRow> summaries;
};

struct CliOptions {
    fs::path data_root = "/Users/nigelli/Desktop/Columbia MAFN/26Spring/MATH5360/Final Project/MATH5360_Final_Project/data";
    fs::path out_dir = "/Users/nigelli/Desktop/Columbia MAFN/26Spring/MATH5360/Final Project/MATH5360_Final_Project/results_cpp";
    fs::path data_file;
    std::string mode = "both";
    std::string grid_mode = "quick";
    int bar_minutes = 5;
    int is_years = 4;
    int oos_quarters = 1;
    int reference_bars_back = 17001;
    double reference_split_ratio = 0.70;
    std::string reference_is_start;
    std::string reference_is_end;
    std::string reference_oos_start;
    std::string reference_oos_end;
    bool verbose = true;
    std::vector<std::string> markets = {"TY", "BTC"};
    double ty_round_turn_cost = std::numeric_limits<double>::quiet_NaN();
    double btc_round_turn_cost = std::numeric_limits<double>::quiet_NaN();
};

SummaryRow summarize_series_rows(
    const std::vector<SeriesRow>& rows,
    const MarketSpec& spec,
    const std::string& run_type,
    int periods,
    int L,
    double S,
    int closed_trades
);

std::string trim(const std::string& input) {
    const auto first = input.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) {
        return "";
    }
    const auto last = input.find_last_not_of(" \t\r\n");
    return input.substr(first, last - first + 1);
}

std::string lower(std::string input) {
    std::transform(input.begin(), input.end(), input.begin(), [](unsigned char ch) {
        return static_cast<char>(std::tolower(ch));
    });
    return input;
}

std::vector<std::string> split_csv_line(const std::string& line) {
    std::vector<std::string> out;
    std::stringstream ss(line);
    std::string item;
    while (std::getline(ss, item, ',')) {
        out.push_back(trim(item));
    }
    if (!line.empty() && line.back() == ',') {
        out.push_back("");
    }
    return out;
}

int hhmm_to_minutes(const std::string& hhmm) {
    if (hhmm.size() < 4) {
        return 0;
    }
    const int hour = std::stoi(hhmm.substr(0, 2));
    const int minute = std::stoi(hhmm.substr(3, 2));
    return hour * 60 + minute;
}

double nearest_double(const std::vector<double>& values, double target) {
    if (values.empty()) {
        return target;
    }
    double best = values.front();
    double best_dist = std::abs(best - target);
    for (double value : values) {
        const double dist = std::abs(value - target);
        if (dist < best_dist) {
            best = value;
            best_dist = dist;
        }
    }
    return best;
}

int nearest_int(const std::vector<int>& values, int target) {
    if (values.empty()) {
        return target;
    }
    int best = values.front();
    int best_dist = std::abs(best - target);
    for (int value : values) {
        const int dist = std::abs(value - target);
        if (dist < best_dist) {
            best = value;
            best_dist = dist;
        }
    }
    return best;
}

int date_key(const std::string& mmddyyyy) {
    if (mmddyyyy.size() < 10) {
        return 0;
    }
    const int month = std::stoi(mmddyyyy.substr(0, 2));
    const int day = std::stoi(mmddyyyy.substr(3, 2));
    const int year = std::stoi(mmddyyyy.substr(6, 4));
    return year * 10000 + month * 100 + day;
}

std::string add_days_mmddyyyy(const std::string& mmddyyyy, int days) {
    std::tm tm = {};
    std::istringstream iss(mmddyyyy);
    iss >> std::get_time(&tm, "%m/%d/%Y");
    if (iss.fail()) {
        throw std::runtime_error("Could not parse date: " + mmddyyyy);
    }
    tm.tm_hour = 0;
    tm.tm_min = 0;
    tm.tm_sec = 0;
    tm.tm_isdst = -1;
    std::time_t raw = std::mktime(&tm);
    if (raw == static_cast<std::time_t>(-1)) {
        throw std::runtime_error("Could not convert date: " + mmddyyyy);
    }
    raw += static_cast<std::time_t>(days) * 24 * 60 * 60;
    std::tm* out_tm = std::localtime(&raw);
    if (out_tm == nullptr) {
        throw std::runtime_error("Could not increment date: " + mmddyyyy);
    }
    std::ostringstream oss;
    oss << std::put_time(out_tm, "%m/%d/%Y");
    return oss.str();
}

MarketSpec make_ty() {
    MarketSpec spec;
    spec.ticker = "TY";
    spec.name = "10-Year Treasury";
    spec.point_value = 1000.0;
    spec.tick_value = 15.625;
    spec.round_turn_cost = 18.625;
    spec.initial_equity = 100000.0;
    spec.use_session_filter = true;
    spec.session_start_min = hhmm_to_minutes("07:20");
    spec.session_end_min = hhmm_to_minutes("14:00");
    spec.session_minutes = 400;
    spec.bars_per_session = 80;
    spec.trading_days_per_year = 252;
    spec.professor_tau = 1440;
    spec.expected_start_key = 19830103;
    spec.min_plausible_price = 50.0;
    spec.professor_stop = 0.02;
    spec.quick_L = {960, 1280, 1440, 1600, 1920, 2240, 3200};
    spec.quick_S = {0.01, 0.015, 0.02, 0.03, 0.04};
    spec.cost_note =
        "Official TF Data TY round-turn cost = $18.625 per contract.";
    return spec;
}

MarketSpec make_btc() {
    MarketSpec spec;
    spec.ticker = "BTC";
    spec.name = "Bitcoin";
    spec.point_value = 5.0;
    spec.tick_value = 25.0;
    spec.round_turn_cost = 25.0;
    spec.initial_equity = 100000.0;
    spec.use_session_filter = true;
    spec.session_start_min = 0;
    spec.session_end_min = hhmm_to_minutes("16:00");
    spec.session_start_min = hhmm_to_minutes("17:00");
    spec.session_minutes = 23 * 60;
    spec.bars_per_session = 276;
    spec.trading_days_per_year = 365;
    spec.professor_tau = 1104;
    spec.expected_start_key = 20171218;
    spec.min_plausible_price = 1000.0;
    spec.professor_stop = 0.03;
    spec.quick_L = {276, 552, 828, 1104, 1380, 1656, 2208};
    spec.quick_S = {0.01, 0.02, 0.03, 0.04, 0.05, 0.06};
    spec.cost_note =
        "Official TF Data BTC round-turn cost = $25.00 per contract; Bloomberg DES implies a 5-point minimum tick, or $25 per minimum fluctuation.";
    return spec;
}

int scale_5m_bars(const int base_bars, const int active_bar_minutes) {
    return std::max(1, static_cast<int>(std::llround(base_bars * 5.0 / static_cast<double>(active_bar_minutes))));
}

std::vector<int> strict_L_grid(const int active_bar_minutes) {
    std::vector<int> out;
    out.reserve(951);
    for (int value = 500; value <= 10000; value += 10) {
        out.push_back(scale_5m_bars(value, active_bar_minutes));
    }
    return out;
}

std::vector<double> strict_S_grid() {
    std::vector<double> out;
    out.reserve(96);
    for (int milli = 5; milli <= 100; ++milli) {
        out.push_back(static_cast<double>(milli) / 1000.0);
    }
    return out;
}

std::vector<int> active_L_grid(const MarketSpec& spec, const CliOptions& options) {
    if (lower(options.grid_mode) == "strict") {
        return strict_L_grid(spec.active_bar_minutes);
    }
    std::vector<int> out;
    out.reserve(spec.quick_L.size());
    for (int value : spec.quick_L) {
        out.push_back(scale_5m_bars(value, spec.active_bar_minutes));
    }
    return out;
}

std::vector<double> active_S_grid(const MarketSpec& spec, const CliOptions& options) {
    if (lower(options.grid_mode) == "strict") {
        return strict_S_grid();
    }
    return spec.quick_S;
}

MarketSpec get_market_spec(const std::string& ticker, const CliOptions& options) {
    const std::string key = lower(ticker);
    if (key == "ty") {
        MarketSpec spec = make_ty();
        if (std::isfinite(options.ty_round_turn_cost)) {
            spec.round_turn_cost = options.ty_round_turn_cost;
            spec.cost_note = "TY round-turn cost overridden from the command line.";
        }
        return spec;
    }
    if (key == "btc") {
        MarketSpec spec = make_btc();
        if (std::isfinite(options.btc_round_turn_cost)) {
            spec.round_turn_cost = options.btc_round_turn_cost;
            spec.cost_note = "BTC round-turn cost overridden from the command line.";
        }
        return spec;
    }
    throw std::runtime_error("Unsupported market: " + ticker);
}

bool bar_in_session(const Bar& bar, const MarketSpec& spec) {
    if (!spec.use_session_filter) {
        return true;
    }
    const int minute_of_day = hhmm_to_minutes(bar.time);
    if (spec.session_start_min <= spec.session_end_min) {
        return minute_of_day > spec.session_start_min && minute_of_day <= spec.session_end_min;
    }
    return minute_of_day > spec.session_start_min || minute_of_day <= spec.session_end_min;
}

std::vector<Bar> load_bars(const fs::path& data_root, const MarketSpec& spec, const CliOptions& options) {
    fs::path path;
    if (!options.data_file.empty()) {
        path = options.data_file;
    } else if (fs::is_regular_file(data_root)) {
        path = data_root;
    } else {
        path = data_root / (spec.ticker + "-" + std::to_string(options.bar_minutes) + "minHLV.csv");
    }
    std::ifstream file(path);
    if (!file) {
        throw std::runtime_error("Could not open data file: " + path.string());
    }

    std::string header_line;
    if (!std::getline(file, header_line)) {
        throw std::runtime_error("Data file is empty: " + path.string());
    }
    const std::vector<std::string> header = split_csv_line(header_line);
    std::map<std::string, std::size_t> idx;
    for (std::size_t i = 0; i < header.size(); ++i) {
        idx[lower(header[i])] = i;
    }

    const auto require_index = [&](const std::string& key) -> std::size_t {
        const auto it = idx.find(key);
        if (it == idx.end()) {
            throw std::runtime_error("Missing required column '" + key + "' in " + path.string());
        }
        return it->second;
    };

    const std::size_t date_idx = require_index("date");
    const std::size_t time_idx = require_index("time");
    const std::size_t open_idx = require_index("open");
    const std::size_t high_idx = require_index("high");
    const std::size_t low_idx = require_index("low");
    const std::size_t close_idx = require_index("close");
    const std::size_t volume_idx = idx.count("volume") ? idx["volume"] : header.size();

    std::vector<Bar> bars;
    std::string line;
    while (std::getline(file, line)) {
        if (trim(line).empty()) {
            continue;
        }
        const std::vector<std::string> parts = split_csv_line(line);
        const auto get_field = [&](std::size_t field_idx) -> std::string {
            return field_idx < parts.size() ? parts[field_idx] : "";
        };

        Bar bar;
        bar.date = get_field(date_idx);
        bar.time = get_field(time_idx);
        bar.datetime = bar.date + " " + bar.time;
        bar.open = std::stod(get_field(open_idx));
        bar.high = std::stod(get_field(high_idx));
        bar.low = std::stod(get_field(low_idx));
        bar.close = std::stod(get_field(close_idx));
        bar.volume = (volume_idx < parts.size() && !get_field(volume_idx).empty())
            ? std::stod(get_field(volume_idx))
            : 0.0;

        if (bar_in_session(bar, spec)) {
            bars.push_back(bar);
        }
    }

    if (bars.empty()) {
        throw std::runtime_error("No bars loaded for " + spec.ticker + " after session filtering.");
    }
    return bars;
}

int infer_bar_minutes(const std::vector<Bar>& bars) {
    std::map<int, int> counts;
    for (std::size_t i = 1; i < bars.size(); ++i) {
        if (bars[i].date != bars[i - 1].date) {
            continue;
        }
        const int prev = hhmm_to_minutes(bars[i - 1].time);
        const int curr = hhmm_to_minutes(bars[i].time);
        const int diff = curr - prev;
        if (diff > 0 && diff <= 120) {
            counts[diff] += 1;
        }
    }
    if (counts.empty()) {
        return 5;
    }
    int best_minutes = counts.begin()->first;
    int best_count = counts.begin()->second;
    for (const auto& [mins, count] : counts) {
        if (count > best_count) {
            best_minutes = mins;
            best_count = count;
        }
    }
    return best_minutes;
}

int infer_typical_bars_per_day(const std::vector<Bar>& bars) {
    std::vector<int> counts;
    counts.reserve(bars.size() / 100);
    std::string current_date;
    int current_count = 0;
    for (const Bar& bar : bars) {
        if (bar.date != current_date) {
            if (!current_date.empty()) {
                counts.push_back(current_count);
            }
            current_date = bar.date;
            current_count = 0;
        }
        ++current_count;
    }
    if (current_count > 0) {
        counts.push_back(current_count);
    }
    if (counts.empty()) {
        return 0;
    }
    std::sort(counts.begin(), counts.end());
    return counts[counts.size() / 2];
}

void finalize_market_spec_for_data(MarketSpec& spec, const std::vector<Bar>& bars) {
    spec.active_bar_minutes = infer_bar_minutes(bars);
    spec.professor_tau = scale_5m_bars(spec.professor_tau, spec.active_bar_minutes);
    const int typical = infer_typical_bars_per_day(bars);
    if (typical > 0) {
        spec.bars_per_session = typical;
    } else {
        spec.bars_per_session = std::max(1, spec.session_minutes / std::max(1, spec.active_bar_minutes));
    }
}

void validate_market_data(const std::vector<Bar>& bars, const MarketSpec& spec, const fs::path& path) {
    if (bars.empty()) {
        throw std::runtime_error("No bars loaded for " + spec.ticker + " from " + path.string());
    }
    const int first_key = date_key(bars.front().date);
    double max_close = bars.front().close;
    for (const Bar& bar : bars) {
        max_close = std::max(max_close, bar.close);
    }
    if (spec.expected_start_key > 0 && first_key < spec.expected_start_key) {
        throw std::runtime_error(
            spec.ticker + " data file appears inconsistent with market inception: " + path.string() +
            " starts at " + bars.front().date + "."
        );
    }
    if (spec.min_plausible_price > 0.0 && max_close < spec.min_plausible_price) {
        throw std::runtime_error(
            spec.ticker + " data file appears inconsistent with expected price scale: " + path.string() +
            " has max close " + std::to_string(max_close) + "."
        );
    }
}

double compute_max_drawdown(const std::vector<double>& equity) {
    if (equity.empty()) {
        return 0.0;
    }
    double peak = equity.front();
    double min_dd = 0.0;
    for (double value : equity) {
        peak = std::max(peak, value);
        min_dd = std::min(min_dd, value - peak);
    }
    return std::abs(min_dd);
}

std::vector<double> compute_drawdown(const std::vector<double>& equity) {
    std::vector<double> dd(equity.size(), 0.0);
    if (equity.empty()) {
        return dd;
    }
    double peak = equity.front();
    for (std::size_t i = 0; i < equity.size(); ++i) {
        peak = std::max(peak, equity[i]);
        dd[i] = equity[i] - peak;
    }
    return dd;
}

IndexBounds matlab_style_date_bounds(
    const std::vector<Bar>& bars,
    const std::string& start_date,
    const std::string& end_date,
    int bars_back
) {
    const int start_key = date_key(start_date);
    const int end_next_key = date_key(add_days_mmddyyyy(end_date, 1));

    int start_idx = 0;
    while (start_idx < static_cast<int>(bars.size()) && date_key(bars[start_idx].date) < start_key) {
        ++start_idx;
    }
    start_idx = std::max(start_idx, std::max(0, bars_back - 1));

    int end_exclusive = 0;
    while (end_exclusive < static_cast<int>(bars.size()) && date_key(bars[end_exclusive].date) < end_next_key) {
        ++end_exclusive;
    }
    end_exclusive = std::max(end_exclusive, bars_back);
    end_exclusive = std::min(end_exclusive, static_cast<int>(bars.size()));

    if (end_exclusive <= start_idx) {
        throw std::runtime_error(
            "Invalid Matlab-style bounds for " + start_date + " to " + end_date +
            ": start_idx=" + std::to_string(start_idx) +
            ", end_exclusive=" + std::to_string(end_exclusive)
        );
    }
    return {start_idx, end_exclusive};
}

ReferenceRunConfig derive_reference_config(
    const std::vector<Bar>& bars,
    const MarketSpec& spec,
    const CliOptions& options
) {
    ReferenceRunConfig config;
    config.market = spec.ticker;
    config.bars_back = options.reference_bars_back;
    config.split_ratio = options.reference_split_ratio;

    const bool has_manual_dates = !options.reference_is_start.empty() &&
        !options.reference_is_end.empty() &&
        !options.reference_oos_start.empty() &&
        !options.reference_oos_end.empty();
    if (has_manual_dates) {
        config.is_start = options.reference_is_start;
        config.is_end = options.reference_is_end;
        config.oos_start = options.reference_oos_start;
        config.oos_end = options.reference_oos_end;
        config.source = "cli_dates";
        return config;
    }

    std::vector<std::string> unique_dates;
    unique_dates.reserve(bars.size() / std::max(1, spec.bars_per_session));
    std::string prev_date;
    for (const Bar& bar : bars) {
        if (bar.date != prev_date) {
            unique_dates.push_back(bar.date);
            prev_date = bar.date;
        }
    }
    if (unique_dates.size() < 2) {
        throw std::runtime_error("Need at least two trading dates to derive a reference split for " + spec.ticker);
    }

    int split_pos = static_cast<int>(std::floor(unique_dates.size() * options.reference_split_ratio));
    split_pos = std::min(std::max(split_pos, 1), static_cast<int>(unique_dates.size()) - 1);
    config.is_start = unique_dates.front();
    config.is_end = unique_dates[split_pos - 1];
    config.oos_start = unique_dates[split_pos];
    config.oos_end = unique_dates.back();
    config.source = "auto_dates";
    return config;
}

double sample_std_slice(const std::vector<double>& values, int start_idx, int end_exclusive) {
    const int n = end_exclusive - start_idx;
    if (n <= 1) {
        return 0.0;
    }
    double mean = 0.0;
    for (int i = start_idx; i < end_exclusive; ++i) {
        mean += values[i];
    }
    mean /= static_cast<double>(n);

    double ss = 0.0;
    for (int i = start_idx; i < end_exclusive; ++i) {
        const double diff = values[i] - mean;
        ss += diff * diff;
    }
    return std::sqrt(ss / static_cast<double>(n - 1));
}

double sum_slice(const std::vector<double>& values, int start_idx, int end_exclusive) {
    double total = 0.0;
    for (int i = start_idx; i < end_exclusive; ++i) {
        total += values[i];
    }
    return total;
}

ReferenceSliceStats summarise_reference_slice(
    const BacktestResult& result,
    int start_idx,
    int end_exclusive
) {
    if (!(0 <= start_idx && start_idx < end_exclusive && end_exclusive <= static_cast<int>(result.net_equity.size()))) {
        throw std::runtime_error("Reference slice is out of bounds.");
    }

    ReferenceSliceStats stats;
    stats.start_idx = start_idx;
    stats.end_exclusive = end_exclusive;
    stats.gross_profit = result.gross_equity[end_exclusive - 1] - result.gross_equity[start_idx];
    stats.net_profit = result.net_equity[end_exclusive - 1] - result.net_equity[start_idx];

    double gross_min_dd = 0.0;
    double net_min_dd = 0.0;
    for (int i = start_idx; i < end_exclusive; ++i) {
        gross_min_dd = std::min(gross_min_dd, result.gross_drawdown[i]);
        net_min_dd = std::min(net_min_dd, result.net_drawdown[i]);
    }
    stats.gross_worst_drawdown = std::abs(gross_min_dd);
    stats.net_worst_drawdown = std::abs(net_min_dd);
    stats.gross_stdev = sample_std_slice(result.gross_bar_pnl, start_idx, end_exclusive);
    stats.net_stdev = sample_std_slice(result.net_bar_pnl, start_idx, end_exclusive);
    stats.trade_units = sum_slice(result.trade_units, start_idx, end_exclusive);
    stats.gross_objective = stats.gross_worst_drawdown > 0.0 ? stats.gross_profit / stats.gross_worst_drawdown : 0.0;
    stats.net_objective = stats.net_worst_drawdown > 0.0 ? stats.net_profit / stats.net_worst_drawdown : 0.0;
    return stats;
}

int count_closed_trades_in_slice(const std::vector<TradeRecord>& trades, int start_idx, int end_exclusive) {
    int total = 0;
    for (const TradeRecord& trade : trades) {
        if (trade.exit_bar >= start_idx && trade.exit_bar < end_exclusive) {
            ++total;
        }
    }
    return total;
}

BacktestResult run_tf_backtest(
    const std::vector<Bar>& bars,
    const MarketSpec& spec,
    const TfParams& params,
    int eval_start,
    int eval_end,
    int warmup_bars = -1,
    int bars_back_override = -1,
    bool rebase_at_eval_start = true
) {
    BacktestResult result;
    result.params = params;

    const int n = static_cast<int>(bars.size());
    if (eval_start < 0) {
        eval_start = 0;
    }
    if (eval_end <= 0 || eval_end > n) {
        eval_end = n;
    }
    if (warmup_bars < 0) {
        warmup_bars = params.L + 1;
    }

    const int slice_start = std::max(0, eval_start - warmup_bars);
    const int slice_end = eval_end;
    const int local_eval_start = eval_start - slice_start;
    const int slice_n = slice_end - slice_start;
    const int min_len = std::max({params.L, warmup_bars, 100}) + 5;

    if (slice_n < min_len) {
        result.error = true;
        result.why = "slice too short";
        return result;
    }

    result.slice_start = slice_start;
    result.eval_start = eval_start;
    result.eval_end = eval_end;
    result.warmup_bars = warmup_bars;

    std::vector<double> open(slice_n), high(slice_n), low(slice_n), close(slice_n);
    for (int i = 0; i < slice_n; ++i) {
        const Bar& bar = bars[slice_start + i];
        open[i] = bar.open;
        high[i] = bar.high;
        low[i] = bar.low;
        close[i] = bar.close;
    }

    std::vector<double> hh(slice_n, 0.0), ll(slice_n, 0.0);
    for (int k = params.L; k < slice_n; ++k) {
        double h_max = high[k - params.L];
        double l_min = low[k - params.L];
        for (int j = k - params.L + 1; j < k; ++j) {
            h_max = std::max(h_max, high[j]);
            l_min = std::min(l_min, low[j]);
        }
        hh[k] = h_max;
        ll[k] = l_min;
    }

    result.gross_equity.assign(slice_n, spec.initial_equity);
    result.net_equity.assign(slice_n, spec.initial_equity);
    result.gross_drawdown.assign(slice_n, 0.0);
    result.net_drawdown.assign(slice_n, 0.0);
    result.position.assign(slice_n, 0);
    result.gross_bar_pnl.assign(slice_n, 0.0);
    result.net_bar_pnl.assign(slice_n, 0.0);
    result.transaction_cost.assign(slice_n, 0.0);
    result.turnover_contracts.assign(slice_n, 0.0);
    result.turnover_notional.assign(slice_n, 0.0);
    result.trade_units.assign(slice_n, 0.0);

    int position = 0;
    int open_entry_bar = -1;
    double open_entry_px = 0.0;
    int open_dir = 0;
    double benchmark_long = 0.0;
    double benchmark_short = 0.0;
    const double side_cost = spec.round_turn_cost / 2.0;
    const int bars_back = (bars_back_override >= 0) ? bars_back_override : std::max(100, local_eval_start);
    const int start_k = std::max(params.L, bars_back);

    for (int k = start_k; k < slice_n; ++k) {
        double gross_delta = spec.point_value * (close[k] - close[k - 1]) * static_cast<double>(position);
        double trade_cost = 0.0;
        double turnover_contracts = 0.0;
        double turnover_notional = 0.0;
        const int position_before = position;

        if (position == 0) {
            const bool buy = high[k] >= hh[k];
            const bool sell = low[k] <= ll[k];

            if (buy && sell) {
                gross_delta = spec.point_value * (ll[k] - hh[k]);
                trade_cost = spec.round_turn_cost;
                turnover_contracts = 2.0;
                turnover_notional = std::abs(hh[k] * spec.point_value) + std::abs(ll[k] * spec.point_value);
                result.trade_units[k] = 1.0;

                TradeRecord trade;
                trade.entry_bar = slice_start + k;
                trade.exit_bar = slice_start + k;
                trade.entry_time = bars[slice_start + k].datetime;
                trade.exit_time = bars[slice_start + k].datetime;
                trade.direction = 1;
                trade.entry_price = hh[k];
                trade.exit_price = ll[k];
                trade.duration_bars = 0;
                trade.gross_pnl = spec.point_value * (ll[k] - hh[k]);
                trade.transaction_cost = spec.round_turn_cost;
                trade.net_pnl = trade.gross_pnl - trade.transaction_cost;
                trade.turnover_contracts = 2.0;
                trade.turnover_notional = turnover_notional;
                trade.is_oos = (k >= local_eval_start);
                result.ledger.push_back(trade);
            } else if (buy) {
                gross_delta = spec.point_value * (close[k] - hh[k]);
                trade_cost = side_cost;
                turnover_contracts = 1.0;
                turnover_notional = std::abs(hh[k] * spec.point_value);
                result.trade_units[k] = 0.5;

                position = 1;
                benchmark_long = high[k];
                open_entry_bar = k;
                open_entry_px = hh[k];
                open_dir = 1;
            } else if (sell) {
                gross_delta = -spec.point_value * (close[k] - ll[k]);
                trade_cost = side_cost;
                turnover_contracts = 1.0;
                turnover_notional = std::abs(ll[k] * spec.point_value);
                result.trade_units[k] = 0.5;

                position = -1;
                benchmark_short = low[k];
                open_entry_bar = k;
                open_entry_px = ll[k];
                open_dir = -1;
            }
        } else if (position == 1) {
            const bool sell_short = low[k] <= ll[k];
            const bool sell_stop = low[k] <= benchmark_long * (1.0 - params.S);

            if (sell_short && sell_stop) {
                gross_delta = gross_delta - 2.0 * spec.point_value * (close[k] - ll[k]);
                trade_cost = spec.round_turn_cost;
                turnover_contracts = 2.0;
                turnover_notional = 2.0 * std::abs(ll[k] * spec.point_value);
                result.trade_units[k] = 1.0;

                TradeRecord trade;
                trade.entry_bar = slice_start + open_entry_bar;
                trade.exit_bar = slice_start + k;
                trade.entry_time = bars[slice_start + open_entry_bar].datetime;
                trade.exit_time = bars[slice_start + k].datetime;
                trade.direction = open_dir;
                trade.entry_price = open_entry_px;
                trade.exit_price = ll[k];
                trade.duration_bars = k - open_entry_bar;
                trade.gross_pnl = spec.point_value * (ll[k] - open_entry_px) * static_cast<double>(open_dir);
                trade.transaction_cost = spec.round_turn_cost;
                trade.net_pnl = trade.gross_pnl - trade.transaction_cost;
                trade.turnover_contracts = 2.0;
                trade.turnover_notional = std::abs(open_entry_px * spec.point_value) + std::abs(ll[k] * spec.point_value);
                trade.is_oos = (k >= local_eval_start);
                result.ledger.push_back(trade);

                position = -1;
                benchmark_short = low[k];
                open_entry_bar = k;
                open_entry_px = ll[k];
                open_dir = -1;
            } else {
                if (sell_stop) {
                    const double exit_px = benchmark_long * (1.0 - params.S);
                    gross_delta = gross_delta - spec.point_value * (close[k] - exit_px);
                    trade_cost = side_cost;
                    turnover_contracts = 1.0;
                    turnover_notional = std::abs(exit_px * spec.point_value);
                    result.trade_units[k] = 0.5;

                    TradeRecord trade;
                    trade.entry_bar = slice_start + open_entry_bar;
                    trade.exit_bar = slice_start + k;
                    trade.entry_time = bars[slice_start + open_entry_bar].datetime;
                    trade.exit_time = bars[slice_start + k].datetime;
                    trade.direction = open_dir;
                    trade.entry_price = open_entry_px;
                    trade.exit_price = exit_px;
                    trade.duration_bars = k - open_entry_bar;
                    trade.gross_pnl = spec.point_value * (exit_px - open_entry_px) * static_cast<double>(open_dir);
                    trade.transaction_cost = spec.round_turn_cost;
                    trade.net_pnl = trade.gross_pnl - trade.transaction_cost;
                    trade.turnover_contracts = 2.0;
                    trade.turnover_notional = std::abs(open_entry_px * spec.point_value) + std::abs(exit_px * spec.point_value);
                    trade.is_oos = (k >= local_eval_start);
                    result.ledger.push_back(trade);

                    position = 0;
                    open_entry_bar = -1;
                    open_entry_px = 0.0;
                    open_dir = 0;
                } else if (sell_short) {
                    gross_delta = gross_delta - 2.0 * spec.point_value * (close[k] - ll[k]);
                    trade_cost = spec.round_turn_cost;
                    turnover_contracts = 2.0;
                    turnover_notional = 2.0 * std::abs(ll[k] * spec.point_value);
                    result.trade_units[k] = 1.0;

                    TradeRecord trade;
                    trade.entry_bar = slice_start + open_entry_bar;
                    trade.exit_bar = slice_start + k;
                    trade.entry_time = bars[slice_start + open_entry_bar].datetime;
                    trade.exit_time = bars[slice_start + k].datetime;
                    trade.direction = open_dir;
                    trade.entry_price = open_entry_px;
                    trade.exit_price = ll[k];
                    trade.duration_bars = k - open_entry_bar;
                    trade.gross_pnl = spec.point_value * (ll[k] - open_entry_px) * static_cast<double>(open_dir);
                    trade.transaction_cost = spec.round_turn_cost;
                    trade.net_pnl = trade.gross_pnl - trade.transaction_cost;
                    trade.turnover_contracts = 2.0;
                    trade.turnover_notional = std::abs(open_entry_px * spec.point_value) + std::abs(ll[k] * spec.point_value);
                    trade.is_oos = (k >= local_eval_start);
                    result.ledger.push_back(trade);

                    position = -1;
                    benchmark_short = low[k];
                    open_entry_bar = k;
                    open_entry_px = ll[k];
                    open_dir = -1;
                }
            }
            benchmark_long = std::max(high[k], benchmark_long);
        } else if (position == -1) {
            const bool buy_long = high[k] >= hh[k];
            const bool buy_stop = high[k] >= benchmark_short * (1.0 + params.S);

            if (buy_long && buy_stop) {
                gross_delta = gross_delta + 2.0 * spec.point_value * (close[k] - hh[k]);
                trade_cost = spec.round_turn_cost;
                turnover_contracts = 2.0;
                turnover_notional = 2.0 * std::abs(hh[k] * spec.point_value);
                result.trade_units[k] = 1.0;

                TradeRecord trade;
                trade.entry_bar = slice_start + open_entry_bar;
                trade.exit_bar = slice_start + k;
                trade.entry_time = bars[slice_start + open_entry_bar].datetime;
                trade.exit_time = bars[slice_start + k].datetime;
                trade.direction = open_dir;
                trade.entry_price = open_entry_px;
                trade.exit_price = hh[k];
                trade.duration_bars = k - open_entry_bar;
                trade.gross_pnl = spec.point_value * (hh[k] - open_entry_px) * static_cast<double>(open_dir);
                trade.transaction_cost = spec.round_turn_cost;
                trade.net_pnl = trade.gross_pnl - trade.transaction_cost;
                trade.turnover_contracts = 2.0;
                trade.turnover_notional = std::abs(open_entry_px * spec.point_value) + std::abs(hh[k] * spec.point_value);
                trade.is_oos = (k >= local_eval_start);
                result.ledger.push_back(trade);

                position = 1;
                benchmark_long = high[k];
                open_entry_bar = k;
                open_entry_px = hh[k];
                open_dir = 1;
            } else {
                if (buy_stop) {
                    const double exit_px = benchmark_short * (1.0 + params.S);
                    gross_delta = gross_delta + spec.point_value * (close[k] - exit_px);
                    trade_cost = side_cost;
                    turnover_contracts = 1.0;
                    turnover_notional = std::abs(exit_px * spec.point_value);
                    result.trade_units[k] = 0.5;

                    TradeRecord trade;
                    trade.entry_bar = slice_start + open_entry_bar;
                    trade.exit_bar = slice_start + k;
                    trade.entry_time = bars[slice_start + open_entry_bar].datetime;
                    trade.exit_time = bars[slice_start + k].datetime;
                    trade.direction = open_dir;
                    trade.entry_price = open_entry_px;
                    trade.exit_price = exit_px;
                    trade.duration_bars = k - open_entry_bar;
                    trade.gross_pnl = spec.point_value * (exit_px - open_entry_px) * static_cast<double>(open_dir);
                    trade.transaction_cost = spec.round_turn_cost;
                    trade.net_pnl = trade.gross_pnl - trade.transaction_cost;
                    trade.turnover_contracts = 2.0;
                    trade.turnover_notional = std::abs(open_entry_px * spec.point_value) + std::abs(exit_px * spec.point_value);
                    trade.is_oos = (k >= local_eval_start);
                    result.ledger.push_back(trade);

                    position = 0;
                    open_entry_bar = -1;
                    open_entry_px = 0.0;
                    open_dir = 0;
                } else if (buy_long) {
                    gross_delta = gross_delta + 2.0 * spec.point_value * (close[k] - hh[k]);
                    trade_cost = spec.round_turn_cost;
                    turnover_contracts = 2.0;
                    turnover_notional = 2.0 * std::abs(hh[k] * spec.point_value);
                    result.trade_units[k] = 1.0;

                    TradeRecord trade;
                    trade.entry_bar = slice_start + open_entry_bar;
                    trade.exit_bar = slice_start + k;
                    trade.entry_time = bars[slice_start + open_entry_bar].datetime;
                    trade.exit_time = bars[slice_start + k].datetime;
                    trade.direction = open_dir;
                    trade.entry_price = open_entry_px;
                    trade.exit_price = hh[k];
                    trade.duration_bars = k - open_entry_bar;
                    trade.gross_pnl = spec.point_value * (hh[k] - open_entry_px) * static_cast<double>(open_dir);
                    trade.transaction_cost = spec.round_turn_cost;
                    trade.net_pnl = trade.gross_pnl - trade.transaction_cost;
                    trade.turnover_contracts = 2.0;
                    trade.turnover_notional = std::abs(open_entry_px * spec.point_value) + std::abs(hh[k] * spec.point_value);
                    trade.is_oos = (k >= local_eval_start);
                    result.ledger.push_back(trade);

                    position = 1;
                    benchmark_long = high[k];
                    open_entry_bar = k;
                    open_entry_px = hh[k];
                    open_dir = 1;
                }
            }
            benchmark_short = std::min(low[k], benchmark_short);
        }

        const double net_delta = gross_delta - trade_cost;
        result.gross_bar_pnl[k] = gross_delta;
        result.net_bar_pnl[k] = net_delta;
        result.transaction_cost[k] = trade_cost;
        result.turnover_contracts[k] = turnover_contracts;
        result.turnover_notional[k] = turnover_notional;

        result.gross_equity[k] = result.gross_equity[k - 1] + gross_delta;
        result.net_equity[k] = result.net_equity[k - 1] + net_delta;
        result.position[k] = position;

        if (k == 0) {
            result.gross_drawdown[k] = 0.0;
            result.net_drawdown[k] = 0.0;
        }

        if (position_before == 0 && position == 0 && turnover_contracts == 2.0) {
            result.position[k] = 0;
        }
    }

    if (rebase_at_eval_start && local_eval_start > 0) {
        const double net_base = result.net_equity[local_eval_start - 1];
        const double gross_base = result.gross_equity[local_eval_start - 1];
        const double net_offset = net_base - spec.initial_equity;
        const double gross_offset = gross_base - spec.initial_equity;

        for (int k = 0; k < slice_n; ++k) {
            if (k < local_eval_start) {
                result.net_equity[k] = spec.initial_equity;
                result.gross_equity[k] = spec.initial_equity;
                result.net_drawdown[k] = 0.0;
                result.gross_drawdown[k] = 0.0;
            } else {
                result.net_equity[k] -= net_offset;
                result.gross_equity[k] -= gross_offset;
            }
        }
    }

    result.net_drawdown = compute_drawdown(result.net_equity);
    result.gross_drawdown = compute_drawdown(result.gross_equity);
    result.net_profit = result.net_equity.back() - result.net_equity.front();
    result.gross_profit = result.gross_equity.back() - result.gross_equity.front();
    result.net_max_dd = compute_max_drawdown(result.net_equity);
    result.gross_max_dd = compute_max_drawdown(result.gross_equity);
    result.net_objective = result.net_max_dd > 0.0 ? result.net_profit / result.net_max_dd : 0.0;
    result.gross_objective = result.gross_max_dd > 0.0 ? result.gross_profit / result.gross_max_dd : 0.0;
    result.num_closed_trades = static_cast<int>(result.ledger.size());
    result.end_position = position;
    return result;
}

GridSearchResult evaluate_tf_grid(
    const std::vector<Bar>& bars,
    const MarketSpec& spec,
    const std::vector<int>& L_values,
    const std::vector<double>& S_values,
    int eval_start,
    int eval_end
) {
    GridSearchResult out;
    double best_objective = -std::numeric_limits<double>::infinity();
    double best_profit = -std::numeric_limits<double>::infinity();

    for (int L : L_values) {
        for (double S : S_values) {
            ++out.tested;
            const TfParams params{L, S};
            BacktestResult result = run_tf_backtest(bars, spec, params, eval_start, eval_end);
            if (result.error) {
                continue;
            }
            if (!out.valid || result.net_objective > best_objective ||
                (std::abs(result.net_objective - best_objective) < 1e-12 && result.net_profit > best_profit)) {
                out.valid = true;
                out.best_params = params;
                out.best_result = std::move(result);
                best_objective = out.best_result.net_objective;
                best_profit = out.best_result.net_profit;
            }
        }
    }
    return out;
}

TfParams choose_story_config(
    const MarketSpec& spec,
    const std::vector<PeriodRow>& periods,
    const std::vector<int>& L_values,
    const std::vector<double>& S_values
) {
    std::map<std::pair<int, int>, int> counts;
    for (const PeriodRow& row : periods) {
        const int s_key = static_cast<int>(std::llround(row.S * 1000000.0));
        counts[{row.L, s_key}] += 1;
    }
    if (!counts.empty()) {
        auto best_it = counts.begin();
        for (auto it = counts.begin(); it != counts.end(); ++it) {
            if (it->second > best_it->second) {
                best_it = it;
            }
        }
        return TfParams{best_it->first.first, static_cast<double>(best_it->first.second) / 1000000.0};
    }
    return TfParams{
        nearest_int(L_values, spec.professor_tau),
        nearest_double(S_values, spec.professor_stop),
    };
}

std::pair<double, double> append_oos_rows(
    std::vector<SeriesRow>& rows,
    const std::vector<Bar>& bars,
    const MarketSpec& spec,
    const BacktestResult& result,
    int period,
    double cumulative_gross_equity,
    double cumulative_net_equity
) {
    const int local_start = result.eval_start - result.slice_start;
    const int local_end = result.eval_end - result.slice_start;

    for (int i = local_start; i < local_end; ++i) {
        const int global_bar = result.slice_start + i;
        const Bar& bar = bars[global_bar];
        const double prev_gross = cumulative_gross_equity;
        const double prev_net = cumulative_net_equity;
        cumulative_gross_equity += result.gross_bar_pnl[i];
        cumulative_net_equity += result.net_bar_pnl[i];

        const int prev_pos = (i > 0) ? result.position[i - 1] : 0;
        SeriesRow row;
        row.market = spec.ticker;
        row.run_type = "walkforward_oos";
        row.period = period;
        row.datetime = bar.datetime;
        row.date = bar.date;
        row.time = bar.time;
        row.L = result.params.L;
        row.S = result.params.S;
        row.close = bar.close;
        row.position = result.position[i];
        row.delta_position = result.position[i] - prev_pos;
        row.gross_bar_pnl = result.gross_bar_pnl[i];
        row.transaction_cost = result.transaction_cost[i];
        row.net_bar_pnl = result.net_bar_pnl[i];
        row.gross_equity = cumulative_gross_equity;
        row.net_equity = cumulative_net_equity;
        row.gross_return = std::abs(prev_gross) > 1e-12 ? row.gross_bar_pnl / prev_gross : 0.0;
        row.net_return = std::abs(prev_net) > 1e-12 ? row.net_bar_pnl / prev_net : 0.0;
        row.turnover_contracts = result.turnover_contracts[i];
        row.turnover_notional = result.turnover_notional[i];
        row.trade_units = (i < static_cast<int>(result.trade_units.size())) ? result.trade_units[i] : 0.0;
        row.is_oos = true;
        row.segment = "out_of_sample";
        rows.push_back(row);
    }
    return {cumulative_gross_equity, cumulative_net_equity};
}

std::vector<SeriesRow> build_full_sample_rows(
    const std::vector<Bar>& bars,
    const MarketSpec& spec,
    const BacktestResult& result
) {
    std::vector<SeriesRow> rows;
    rows.reserve(bars.size());
    for (std::size_t i = 0; i < bars.size(); ++i) {
        const int prev_pos = (i > 0) ? result.position[i - 1] : 0;
        const double prev_gross = (i > 0) ? result.gross_equity[i - 1] : spec.initial_equity;
        const double prev_net = (i > 0) ? result.net_equity[i - 1] : spec.initial_equity;
        SeriesRow row;
        row.market = spec.ticker;
        row.run_type = "full_sample";
        row.period = 0;
        row.datetime = bars[i].datetime;
        row.date = bars[i].date;
        row.time = bars[i].time;
        row.L = result.params.L;
        row.S = result.params.S;
        row.close = bars[i].close;
        row.position = result.position[i];
        row.delta_position = result.position[i] - prev_pos;
        row.gross_bar_pnl = result.gross_bar_pnl[i];
        row.transaction_cost = result.transaction_cost[i];
        row.net_bar_pnl = result.net_bar_pnl[i];
        row.gross_equity = result.gross_equity[i];
        row.net_equity = result.net_equity[i];
        row.gross_return = std::abs(prev_gross) > 1e-12 ? row.gross_bar_pnl / prev_gross : 0.0;
        row.net_return = std::abs(prev_net) > 1e-12 ? row.net_bar_pnl / prev_net : 0.0;
        row.turnover_contracts = result.turnover_contracts[i];
        row.turnover_notional = result.turnover_notional[i];
        row.trade_units = (i < result.trade_units.size()) ? result.trade_units[i] : 0.0;
        row.is_oos = false;
        row.segment = "full_sample";
        rows.push_back(row);
    }
    return rows;
}

std::vector<SeriesRow> build_reference_rows(
    const std::vector<Bar>& bars,
    const MarketSpec& spec,
    const BacktestResult& result,
    IndexBounds is_bounds,
    IndexBounds oos_bounds
) {
    std::vector<SeriesRow> rows;
    rows.reserve(bars.size());
    for (std::size_t i = 0; i < bars.size(); ++i) {
        const int idx = static_cast<int>(i);
        const int prev_pos = (i > 0) ? result.position[i - 1] : 0;
        const double prev_gross = (i > 0) ? result.gross_equity[i - 1] : spec.initial_equity;
        const double prev_net = (i > 0) ? result.net_equity[i - 1] : spec.initial_equity;
        SeriesRow row;
        row.market = spec.ticker;
        row.run_type = "reference_full";
        row.period = 0;
        row.datetime = bars[i].datetime;
        row.date = bars[i].date;
        row.time = bars[i].time;
        row.L = result.params.L;
        row.S = result.params.S;
        row.close = bars[i].close;
        row.position = result.position[i];
        row.delta_position = result.position[i] - prev_pos;
        row.gross_bar_pnl = result.gross_bar_pnl[i];
        row.transaction_cost = result.transaction_cost[i];
        row.net_bar_pnl = result.net_bar_pnl[i];
        row.gross_equity = result.gross_equity[i];
        row.net_equity = result.net_equity[i];
        row.gross_return = std::abs(prev_gross) > 1e-12 ? row.gross_bar_pnl / prev_gross : 0.0;
        row.net_return = std::abs(prev_net) > 1e-12 ? row.net_bar_pnl / prev_net : 0.0;
        row.turnover_contracts = result.turnover_contracts[i];
        row.turnover_notional = result.turnover_notional[i];
        row.trade_units = (i < result.trade_units.size()) ? result.trade_units[i] : 0.0;
        row.is_oos = idx >= oos_bounds.start_idx && idx < oos_bounds.end_exclusive;
        if (idx < is_bounds.start_idx) {
            row.segment = "pre_is";
        } else if (idx < is_bounds.end_exclusive) {
            row.segment = "in_sample";
        } else if (idx < oos_bounds.end_exclusive && idx >= oos_bounds.start_idx) {
            row.segment = "out_of_sample";
        } else {
            row.segment = "post_oos";
        }
        rows.push_back(row);
    }
    return rows;
}

SummaryRow build_reference_summary(
    const std::vector<Bar>& bars,
    const MarketSpec& spec,
    const TfParams& params,
    const BacktestResult& result,
    const ReferenceSliceStats& stats,
    const std::string& run_type,
    int bars_back
) {
    SummaryRow summary;
    summary.market = spec.ticker;
    summary.run_type = run_type;
    summary.start_time = bars[stats.start_idx].datetime;
    summary.end_time = bars[stats.end_exclusive - 1].datetime;
    summary.bars = stats.end_exclusive - stats.start_idx;
    summary.periods = 1;
    summary.L = params.L;
    summary.S = params.S;
    summary.gross_profit = stats.gross_profit;
    summary.net_profit = stats.net_profit;
    summary.gross_max_dd = stats.gross_worst_drawdown;
    summary.net_max_dd = stats.net_worst_drawdown;
    summary.gross_roa = stats.gross_objective;
    summary.net_roa = stats.net_objective;
    summary.total_cost = sum_slice(result.transaction_cost, stats.start_idx, stats.end_exclusive);
    summary.turnover_contracts = sum_slice(result.turnover_contracts, stats.start_idx, stats.end_exclusive);
    summary.turnover_notional = sum_slice(result.turnover_notional, stats.start_idx, stats.end_exclusive);
    summary.closed_trades = count_closed_trades_in_slice(result.ledger, stats.start_idx, stats.end_exclusive);
    summary.gross_stdev = stats.gross_stdev;
    summary.net_stdev = stats.net_stdev;
    summary.trade_units = stats.trade_units;
    summary.bars_back = bars_back;
    summary.round_turn_cost = spec.round_turn_cost;
    summary.cost_note = spec.cost_note;
    return summary;
}

ReferenceBundle run_reference_split(
    const std::vector<Bar>& bars,
    const MarketSpec& spec,
    const CliOptions& options,
    bool verbose
) {
    ReferenceBundle bundle;
    bundle.config = derive_reference_config(bars, spec, options);
    bundle.is_bounds = matlab_style_date_bounds(
        bars,
        bundle.config.is_start,
        bundle.config.is_end,
        bundle.config.bars_back
    );
    bundle.oos_bounds = matlab_style_date_bounds(
        bars,
        bundle.config.oos_start,
        bundle.config.oos_end,
        bundle.config.bars_back
    );

    double best_objective = -std::numeric_limits<double>::infinity();
    double best_profit = -std::numeric_limits<double>::infinity();
    bool found = false;
    const std::vector<int> L_values = active_L_grid(spec, options);
    const std::vector<double> S_values = active_S_grid(spec, options);

    for (int L : L_values) {
        for (double S : S_values) {
            const TfParams params{L, S};
            BacktestResult result = run_tf_backtest(
                bars,
                spec,
                params,
                0,
                static_cast<int>(bars.size()),
                bundle.config.bars_back,
                bundle.config.bars_back,
                false
            );
            if (result.error) {
                continue;
            }

            const ReferenceSliceStats is_stats = summarise_reference_slice(
                result,
                bundle.is_bounds.start_idx,
                bundle.is_bounds.end_exclusive
            );
            const ReferenceSliceStats oos_stats = summarise_reference_slice(
                result,
                bundle.oos_bounds.start_idx,
                bundle.oos_bounds.end_exclusive
            );

            ReferenceSurfaceRow row;
            row.market = spec.ticker;
            row.L = L;
            row.S = S;
            row.bars_back = bundle.config.bars_back;
            row.is_start = bundle.config.is_start;
            row.is_end = bundle.config.is_end;
            row.oos_start = bundle.config.oos_start;
            row.oos_end = bundle.config.oos_end;
            row.is_gross_profit = is_stats.gross_profit;
            row.is_net_profit = is_stats.net_profit;
            row.is_gross_worst_drawdown = is_stats.gross_worst_drawdown;
            row.is_net_worst_drawdown = is_stats.net_worst_drawdown;
            row.is_gross_stdev = is_stats.gross_stdev;
            row.is_net_stdev = is_stats.net_stdev;
            row.is_trade_units = is_stats.trade_units;
            row.is_gross_objective = is_stats.gross_objective;
            row.is_net_objective = is_stats.net_objective;
            row.oos_gross_profit = oos_stats.gross_profit;
            row.oos_net_profit = oos_stats.net_profit;
            row.oos_gross_worst_drawdown = oos_stats.gross_worst_drawdown;
            row.oos_net_worst_drawdown = oos_stats.net_worst_drawdown;
            row.oos_gross_stdev = oos_stats.gross_stdev;
            row.oos_net_stdev = oos_stats.net_stdev;
            row.oos_trade_units = oos_stats.trade_units;
            row.oos_gross_objective = oos_stats.gross_objective;
            row.oos_net_objective = oos_stats.net_objective;
            bundle.surface.push_back(row);

            if (!found ||
                is_stats.net_objective > best_objective ||
                (std::abs(is_stats.net_objective - best_objective) < 1e-12 && is_stats.net_profit > best_profit)) {
                found = true;
                best_objective = is_stats.net_objective;
                best_profit = is_stats.net_profit;
                bundle.best_params = params;
                bundle.best_result = std::move(result);
                bundle.is_stats = is_stats;
                bundle.oos_stats = oos_stats;
            }
        }
    }

    if (!found) {
        throw std::runtime_error("No valid reference-split TF configuration for " + spec.ticker);
    }

    bundle.series_rows = build_reference_rows(
        bars,
        spec,
        bundle.best_result,
        bundle.is_bounds,
        bundle.oos_bounds
    );
    bundle.trades = bundle.best_result.ledger;
    for (TradeRecord& trade : bundle.trades) {
        trade.market = spec.ticker;
        trade.run_type = "reference_full";
        trade.period = 0;
        trade.L = bundle.best_params.L;
        trade.S = bundle.best_params.S;
    }

    bundle.summaries.push_back(build_reference_summary(
        bars, spec, bundle.best_params, bundle.best_result, bundle.is_stats, "reference_in_sample", bundle.config.bars_back
    ));
    bundle.summaries.push_back(build_reference_summary(
        bars, spec, bundle.best_params, bundle.best_result, bundle.oos_stats, "reference_out_of_sample", bundle.config.bars_back
    ));
    bundle.summaries.push_back(summarize_series_rows(
        bundle.series_rows,
        spec,
        "reference_full",
        1,
        bundle.best_params.L,
        bundle.best_params.S,
        static_cast<int>(bundle.trades.size())
    ));
    bundle.summaries.back().bars_back = bundle.config.bars_back;

    if (verbose) {
        std::cout << "Reference [" << spec.ticker << "] "
                  << bundle.config.is_start << " to " << bundle.config.is_end
                  << " | " << bundle.config.oos_start << " to " << bundle.config.oos_end
                  << " | barsBack=" << bundle.config.bars_back
                  << " | best L=" << bundle.best_params.L
                  << " S=" << std::fixed << std::setprecision(3) << bundle.best_params.S
                  << " | IS net obj=" << std::setprecision(4) << bundle.is_stats.net_objective
                  << " | OOS net obj=" << bundle.oos_stats.net_objective
                  << "\n";
    }

    return bundle;
}

WalkForwardBundle run_walk_forward(
    const std::vector<Bar>& bars,
    const MarketSpec& spec,
    const CliOptions& options,
    int is_years,
    int oos_quarters,
    bool verbose
) {
    WalkForwardBundle bundle;
    const int bars_per_year = spec.bars_per_session * spec.trading_days_per_year;
    const int is_bars = is_years * bars_per_year;
    const int oos_bars = (oos_quarters * bars_per_year) / 4;
    const std::vector<int> L_values = active_L_grid(spec, options);
    const std::vector<double> S_values = active_S_grid(spec, options);

    if (verbose) {
        std::cout << "Walk-Forward [" << spec.ticker << "] "
                  << "IS=" << is_years << "y (" << is_bars << " bars), "
                  << "OOS=" << oos_quarters << "Q (" << oos_bars << " bars), "
                  << "grid=" << options.grid_mode << "\n";
    }

    int idx = 0;
    int period = 1;
    double cum_gross = spec.initial_equity;
    double cum_net = spec.initial_equity;

    while (idx + is_bars + oos_bars <= static_cast<int>(bars.size())) {
        const int is_start = idx;
        const int is_end = is_start + is_bars;
        const int oos_start = is_end;
        const int oos_end = oos_start + oos_bars;

        GridSearchResult best_is = evaluate_tf_grid(bars, spec, L_values, S_values, is_start, is_end);
        if (!best_is.valid) {
            if (verbose) {
                std::cout << "  Period " << period << ": no valid IS configuration\n";
            }
            idx += oos_bars;
            ++period;
            continue;
        }

        BacktestResult best_oos = run_tf_backtest(bars, spec, best_is.best_params, oos_start, oos_end);
        if (best_oos.error) {
            if (verbose) {
                std::cout << "  Period " << period << ": OOS run failed\n";
            }
            idx += oos_bars;
            ++period;
            continue;
        }

        PeriodRow row;
        row.period = period;
        row.market = spec.ticker;
        row.is_start = bars[is_start].datetime;
        row.is_end = bars[is_end - 1].datetime;
        row.oos_start = bars[oos_start].datetime;
        row.oos_end = bars[oos_end - 1].datetime;
        row.L = best_is.best_params.L;
        row.S = best_is.best_params.S;
        row.is_gross_objective = best_is.best_result.gross_objective;
        row.is_net_objective = best_is.best_result.net_objective;
        row.is_gross_profit = best_is.best_result.gross_profit;
        row.is_net_profit = best_is.best_result.net_profit;
        row.is_gross_max_dd = best_is.best_result.gross_max_dd;
        row.is_net_max_dd = best_is.best_result.net_max_dd;
        row.oos_gross_objective = best_oos.gross_objective;
        row.oos_net_objective = best_oos.net_objective;
        row.oos_gross_profit = best_oos.gross_profit;
        row.oos_net_profit = best_oos.net_profit;
        row.oos_gross_max_dd = best_oos.gross_max_dd;
        row.oos_net_max_dd = best_oos.net_max_dd;
        row.oos_closed_trades = static_cast<int>(
            std::count_if(best_oos.ledger.begin(), best_oos.ledger.end(), [](const TradeRecord& trade) {
                return trade.is_oos;
            })
        );
        row.tested = best_is.tested;
        bundle.periods.push_back(row);

        if (verbose) {
            std::cout << "  P" << period
                      << " TF L=" << row.L
                      << " S=" << std::fixed << std::setprecision(3) << row.S
                      << " IS_net_obj=" << std::setprecision(4) << row.is_net_objective
                      << " OOS_net_obj=" << row.oos_net_objective
                      << "\n";
        }

        std::tie(cum_gross, cum_net) = append_oos_rows(
            bundle.oos_rows,
            bars,
            spec,
            best_oos,
            period,
            cum_gross,
            cum_net
        );

        for (TradeRecord trade : best_oos.ledger) {
            if (!trade.is_oos) {
                continue;
            }
            trade.market = spec.ticker;
            trade.run_type = "walkforward_oos";
            trade.period = period;
            trade.L = best_oos.params.L;
            trade.S = best_oos.params.S;
            bundle.oos_trades.push_back(trade);
        }

        idx += oos_bars;
        ++period;
    }

    return bundle;
}

SummaryRow summarize_series_rows(
    const std::vector<SeriesRow>& rows,
    const MarketSpec& spec,
    const std::string& run_type,
    int periods,
    int L,
    double S,
    int closed_trades
) {
    SummaryRow summary;
    summary.market = spec.ticker;
    summary.run_type = run_type;
    summary.bars = static_cast<int>(rows.size());
    summary.periods = periods;
    summary.L = L;
    summary.S = S;
    summary.round_turn_cost = spec.round_turn_cost;
    summary.cost_note = spec.cost_note;

    if (rows.empty()) {
        return summary;
    }

    summary.start_time = rows.front().datetime;
    summary.end_time = rows.back().datetime;
    summary.gross_profit = rows.back().gross_equity - spec.initial_equity;
    summary.net_profit = rows.back().net_equity - spec.initial_equity;
    summary.total_cost = 0.0;
    summary.turnover_contracts = 0.0;
    summary.turnover_notional = 0.0;
    summary.closed_trades = closed_trades;

    std::vector<double> gross_equity;
    std::vector<double> net_equity;
    std::vector<double> gross_bar_pnl;
    std::vector<double> net_bar_pnl;
    gross_equity.reserve(rows.size());
    net_equity.reserve(rows.size());
    for (const SeriesRow& row : rows) {
        summary.total_cost += row.transaction_cost;
        summary.turnover_contracts += row.turnover_contracts;
        summary.turnover_notional += row.turnover_notional;
        summary.trade_units += row.trade_units;
        gross_equity.push_back(row.gross_equity);
        net_equity.push_back(row.net_equity);
        gross_bar_pnl.push_back(row.gross_bar_pnl);
        net_bar_pnl.push_back(row.net_bar_pnl);
    }
    summary.gross_max_dd = compute_max_drawdown(gross_equity);
    summary.net_max_dd = compute_max_drawdown(net_equity);
    summary.gross_roa = summary.gross_max_dd > 0.0 ? summary.gross_profit / summary.gross_max_dd : 0.0;
    summary.net_roa = summary.net_max_dd > 0.0 ? summary.net_profit / summary.net_max_dd : 0.0;
    summary.gross_stdev = sample_std_slice(gross_bar_pnl, 0, static_cast<int>(gross_bar_pnl.size()));
    summary.net_stdev = sample_std_slice(net_bar_pnl, 0, static_cast<int>(net_bar_pnl.size()));
    return summary;
}

void write_series_csv(const fs::path& path, const std::vector<SeriesRow>& rows) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write file: " + path.string());
    }
    out << std::fixed << std::setprecision(6);
    out << "Market,RunType,Period,DateTime,Date,Time,L,S,Close,Position,DeltaPosition,"
           "GrossBarPnL,TransactionCost,NetBarPnL,GrossEquity,NetEquity,GrossReturn,NetReturn,"
           "TurnoverContracts,TurnoverNotional,TradeUnits,IsOOS,Segment\n";
    for (const SeriesRow& row : rows) {
        out << row.market << ','
            << row.run_type << ','
            << row.period << ','
            << row.datetime << ','
            << row.date << ','
            << row.time << ','
            << row.L << ','
            << row.S << ','
            << row.close << ','
            << row.position << ','
            << row.delta_position << ','
            << row.gross_bar_pnl << ','
            << row.transaction_cost << ','
            << row.net_bar_pnl << ','
            << row.gross_equity << ','
            << row.net_equity << ','
            << row.gross_return << ','
            << row.net_return << ','
            << row.turnover_contracts << ','
            << row.turnover_notional << ','
            << row.trade_units << ','
            << (row.is_oos ? 1 : 0) << ','
            << row.segment << '\n';
    }
}

void write_trades_csv(const fs::path& path, const std::vector<TradeRecord>& trades) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write file: " + path.string());
    }
    out << std::fixed << std::setprecision(6);
    out << "Market,RunType,Period,L,S,EntryBar,ExitBar,EntryTime,ExitTime,Direction,EntryPrice,ExitPrice,"
           "DurationBars,GrossPnL,TransactionCost,NetPnL,TurnoverContracts,TurnoverNotional,IsOOS\n";
    for (const TradeRecord& trade : trades) {
        out << trade.market << ','
            << trade.run_type << ','
            << trade.period << ','
            << trade.L << ','
            << trade.S << ','
            << trade.entry_bar << ','
            << trade.exit_bar << ','
            << trade.entry_time << ','
            << trade.exit_time << ','
            << trade.direction << ','
            << trade.entry_price << ','
            << trade.exit_price << ','
            << trade.duration_bars << ','
            << trade.gross_pnl << ','
            << trade.transaction_cost << ','
            << trade.net_pnl << ','
            << trade.turnover_contracts << ','
            << trade.turnover_notional << ','
            << (trade.is_oos ? 1 : 0) << '\n';
    }
}

void write_periods_csv(const fs::path& path, const std::vector<PeriodRow>& periods) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write file: " + path.string());
    }
    out << std::fixed << std::setprecision(6);
    out << "Period,Market,ISStart,ISEnd,OOSStart,OOSEnd,L,S,ISGrossObjective,ISNetObjective,"
           "ISGrossProfit,ISNetProfit,ISGrossMaxDD,ISNetMaxDD,OOSGrossObjective,OOSNetObjective,"
           "OOSGrossProfit,OOSNetProfit,OOSGrossMaxDD,OOSNetMaxDD,OOSClosedTrades,GridCombosTested\n";
    for (const PeriodRow& row : periods) {
        out << row.period << ','
            << row.market << ','
            << row.is_start << ','
            << row.is_end << ','
            << row.oos_start << ','
            << row.oos_end << ','
            << row.L << ','
            << row.S << ','
            << row.is_gross_objective << ','
            << row.is_net_objective << ','
            << row.is_gross_profit << ','
            << row.is_net_profit << ','
            << row.is_gross_max_dd << ','
            << row.is_net_max_dd << ','
            << row.oos_gross_objective << ','
            << row.oos_net_objective << ','
            << row.oos_gross_profit << ','
            << row.oos_net_profit << ','
            << row.oos_gross_max_dd << ','
            << row.oos_net_max_dd << ','
            << row.oos_closed_trades << ','
            << row.tested << '\n';
    }
}

void write_summary_csv(const fs::path& path, const std::vector<SummaryRow>& rows) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write file: " + path.string());
    }
    out << std::fixed << std::setprecision(6);
    out << "Market,RunType,StartTime,EndTime,Bars,Periods,L,S,GrossProfit,NetProfit,GrossMaxDD,NetMaxDD,"
           "GrossRoA,NetRoA,TotalCost,TurnoverContracts,TurnoverNotional,ClosedTrades,GrossStDev,NetStDev,"
           "TradeUnits,BarsBack,RoundTurnCost,CostNote\n";
    for (const SummaryRow& row : rows) {
        out << row.market << ','
            << row.run_type << ','
            << row.start_time << ','
            << row.end_time << ','
            << row.bars << ','
            << row.periods << ','
            << row.L << ','
            << row.S << ','
            << row.gross_profit << ','
            << row.net_profit << ','
            << row.gross_max_dd << ','
            << row.net_max_dd << ','
            << row.gross_roa << ','
            << row.net_roa << ','
            << row.total_cost << ','
            << row.turnover_contracts << ','
            << row.turnover_notional << ','
            << row.closed_trades << ','
            << row.gross_stdev << ','
            << row.net_stdev << ','
            << row.trade_units << ','
            << row.bars_back << ','
            << row.round_turn_cost << ','
            << '"' << row.cost_note << '"' << '\n';
    }
}

void write_reference_surface_csv(const fs::path& path, const std::vector<ReferenceSurfaceRow>& rows) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write file: " + path.string());
    }
    out << std::fixed << std::setprecision(6);
    out << "Market,L,S,BarsBack,ISStart,ISEnd,OOSStart,OOSEnd,ISGrossProfit,ISNetProfit,ISGrossWorstDrawDown,"
           "ISNetWorstDrawDown,ISGrossStDev,ISNetStDev,ISTradeUnits,ISGrossObjective,ISNetObjective,"
           "OOSGrossProfit,OOSNetProfit,OOSGrossWorstDrawDown,OOSNetWorstDrawDown,OOSGrossStDev,OOSNetStDev,"
           "OOSTradeUnits,OOSGrossObjective,OOSNetObjective\n";
    for (const ReferenceSurfaceRow& row : rows) {
        out << row.market << ','
            << row.L << ','
            << row.S << ','
            << row.bars_back << ','
            << row.is_start << ','
            << row.is_end << ','
            << row.oos_start << ','
            << row.oos_end << ','
            << row.is_gross_profit << ','
            << row.is_net_profit << ','
            << row.is_gross_worst_drawdown << ','
            << row.is_net_worst_drawdown << ','
            << row.is_gross_stdev << ','
            << row.is_net_stdev << ','
            << row.is_trade_units << ','
            << row.is_gross_objective << ','
            << row.is_net_objective << ','
            << row.oos_gross_profit << ','
            << row.oos_net_profit << ','
            << row.oos_gross_worst_drawdown << ','
            << row.oos_net_worst_drawdown << ','
            << row.oos_gross_stdev << ','
            << row.oos_net_stdev << ','
            << row.oos_trade_units << ','
            << row.oos_gross_objective << ','
            << row.oos_net_objective << '\n';
    }
}

void write_reference_config_csv(const fs::path& path, const ReferenceRunConfig& config, const TfParams& best_params) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write file: " + path.string());
    }
    out << "Market,ISStart,ISEnd,OOSStart,OOSEnd,BarsBack,SplitRatio,Source,BestL,BestS\n";
    out << config.market << ','
        << config.is_start << ','
        << config.is_end << ','
        << config.oos_start << ','
        << config.oos_end << ','
        << config.bars_back << ','
        << std::fixed << std::setprecision(6) << config.split_ratio << ','
        << config.source << ','
        << best_params.L << ','
        << best_params.S << '\n';
}

std::vector<std::string> split_list(const std::string& text) {
    std::vector<std::string> out;
    std::stringstream ss(text);
    std::string item;
    while (std::getline(ss, item, ',')) {
        if (!trim(item).empty()) {
            out.push_back(trim(item));
        }
    }
    return out;
}

CliOptions parse_cli(int argc, char** argv) {
    CliOptions options;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        auto require_value = [&](const std::string& flag) -> std::string {
            if (i + 1 >= argc) {
                throw std::runtime_error("Missing value for " + flag);
            }
            return argv[++i];
        };

        if (arg == "--data-root") {
            options.data_root = require_value(arg);
        } else if (arg == "--data-file") {
            options.data_file = require_value(arg);
        } else if (arg == "--out-dir") {
            options.out_dir = require_value(arg);
        } else if (arg == "--mode") {
            options.mode = lower(require_value(arg));
        } else if (arg == "--grid-mode") {
            options.grid_mode = lower(require_value(arg));
        } else if (arg == "--bar-minutes") {
            options.bar_minutes = std::stoi(require_value(arg));
        } else if (arg == "--markets") {
            options.markets = split_list(require_value(arg));
        } else if (arg == "--is-years") {
            options.is_years = std::stoi(require_value(arg));
        } else if (arg == "--oos-quarters") {
            options.oos_quarters = std::stoi(require_value(arg));
        } else if (arg == "--reference-bars-back") {
            options.reference_bars_back = std::stoi(require_value(arg));
        } else if (arg == "--reference-split-ratio") {
            options.reference_split_ratio = std::stod(require_value(arg));
        } else if (arg == "--reference-is-start") {
            options.reference_is_start = require_value(arg);
        } else if (arg == "--reference-is-end") {
            options.reference_is_end = require_value(arg);
        } else if (arg == "--reference-oos-start") {
            options.reference_oos_start = require_value(arg);
        } else if (arg == "--reference-oos-end") {
            options.reference_oos_end = require_value(arg);
        } else if (arg == "--ty-rt-cost") {
            options.ty_round_turn_cost = std::stod(require_value(arg));
        } else if (arg == "--btc-rt-cost") {
            options.btc_round_turn_cost = std::stod(require_value(arg));
        } else if (arg == "--quiet") {
            options.verbose = false;
        } else if (arg == "--help") {
            std::cout
                << "Usage: tf_backtest_treasury_btc [options]\n"
                << "  --data-root <path>       Input CSV directory\n"
                << "  --data-file <path>       Explicit CSV file (single-market runs)\n"
                << "  --out-dir <path>         Output directory for CSV files\n"
                << "  --mode <both|walkforward|reference>\n"
                << "  --grid-mode <quick|strict>\n"
                << "  --bar-minutes <int>      Data interval in minutes (default: 5)\n"
                << "  --markets <TY,BTC>       Markets to run, comma-separated\n"
                << "  --is-years <int>         In-sample years per walk-forward period\n"
                << "  --oos-quarters <int>     Out-of-sample quarters per period\n"
                << "  --reference-bars-back <int>\n"
                << "  --reference-split-ratio <double>\n"
                << "  --reference-is-start <MM/DD/YYYY>\n"
                << "  --reference-is-end <MM/DD/YYYY>\n"
                << "  --reference-oos-start <MM/DD/YYYY>\n"
                << "  --reference-oos-end <MM/DD/YYYY>\n"
                << "  --ty-rt-cost <double>    Override TY round-turn cost per contract\n"
                << "  --btc-rt-cost <double>   Override BTC round-turn cost per contract\n"
                << "  --quiet                  Reduce progress logging\n";
            std::exit(0);
        } else {
            throw std::runtime_error("Unknown argument: " + arg);
        }
    }
    if (options.mode != "both" && options.mode != "walkforward" && options.mode != "reference") {
        throw std::runtime_error("mode must be one of: both, walkforward, reference");
    }
    if (options.grid_mode != "quick" && options.grid_mode != "strict") {
        throw std::runtime_error("grid-mode must be one of: quick, strict");
    }
    if (options.bar_minutes <= 0) {
        throw std::runtime_error("bar-minutes must be positive");
    }
    if (!options.data_file.empty() && options.markets.size() != 1) {
        throw std::runtime_error("--data-file may only be used with a single market");
    }
    if (!(options.reference_split_ratio > 0.0 && options.reference_split_ratio < 1.0)) {
        throw std::runtime_error("reference-split-ratio must be strictly between 0 and 1");
    }
    return options;
}

int main(int argc, char** argv) {
    try {
        const CliOptions options = parse_cli(argc, argv);
        fs::create_directories(options.out_dir);
        std::vector<SummaryRow> all_summaries;

        for (const std::string& requested_market : options.markets) {
            MarketSpec spec = get_market_spec(requested_market, options);
            const fs::path source_path = !options.data_file.empty()
                ? options.data_file
                : (fs::is_regular_file(options.data_root)
                    ? options.data_root
                    : (options.data_root / (spec.ticker + "-" + std::to_string(options.bar_minutes) + "minHLV.csv")));
            const std::vector<Bar> bars = load_bars(options.data_root, spec, options);
            validate_market_data(bars, spec, source_path);
            finalize_market_spec_for_data(spec, bars);
            if (options.verbose) {
                std::cout << "\nRunning " << spec.ticker
                          << " (" << spec.name << ") on " << bars.size()
                          << " filtered " << spec.active_bar_minutes << "-minute bars\n";
                std::cout << "Source file: " << source_path << "\n";
                std::cout << "Typical bars/session: " << spec.bars_per_session
                          << " | session minutes: " << spec.session_minutes << "\n";
                std::cout << "Cost model: " << spec.cost_note << "\n";
            }
            const fs::path market_dir = options.out_dir / spec.ticker;
            fs::create_directories(market_dir);
            if (options.mode == "both" || options.mode == "walkforward") {
                WalkForwardBundle wf = run_walk_forward(
                    bars,
                    spec,
                    options,
                    options.is_years,
                    options.oos_quarters,
                    options.verbose
                );
                const std::vector<int> story_L = active_L_grid(spec, options);
                const std::vector<double> story_S = active_S_grid(spec, options);
                const TfParams story_cfg = choose_story_config(spec, wf.periods, story_L, story_S);
                BacktestResult full_sample = run_tf_backtest(
                    bars,
                    spec,
                    story_cfg,
                    0,
                    static_cast<int>(bars.size())
                );
                if (full_sample.error) {
                    throw std::runtime_error("Full-sample backtest failed for " + spec.ticker + ": " + full_sample.why);
                }

                std::vector<SeriesRow> full_rows = build_full_sample_rows(bars, spec, full_sample);
                std::vector<TradeRecord> full_trades = full_sample.ledger;
                for (TradeRecord& trade : full_trades) {
                    trade.market = spec.ticker;
                    trade.run_type = "full_sample";
                    trade.period = 0;
                    trade.L = story_cfg.L;
                    trade.S = story_cfg.S;
                }

                write_periods_csv(market_dir / (spec.ticker + "_tf_walkforward_periods.csv"), wf.periods);
                write_series_csv(market_dir / (spec.ticker + "_tf_oos_returns.csv"), wf.oos_rows);
                write_trades_csv(market_dir / (spec.ticker + "_tf_oos_trades.csv"), wf.oos_trades);
                write_series_csv(market_dir / (spec.ticker + "_tf_fullsample_returns.csv"), full_rows);
                write_trades_csv(market_dir / (spec.ticker + "_tf_fullsample_trades.csv"), full_trades);

                SummaryRow wf_summary = summarize_series_rows(
                    wf.oos_rows,
                    spec,
                    "walkforward_oos",
                    static_cast<int>(wf.periods.size()),
                    story_cfg.L,
                    story_cfg.S,
                    static_cast<int>(wf.oos_trades.size())
                );
                SummaryRow full_summary = summarize_series_rows(
                    full_rows,
                    spec,
                    "full_sample",
                    1,
                    story_cfg.L,
                    story_cfg.S,
                    static_cast<int>(full_trades.size())
                );
                all_summaries.push_back(wf_summary);
                all_summaries.push_back(full_summary);

                if (options.verbose) {
                    std::cout << "  Story config: L=" << story_cfg.L
                              << " S=" << std::fixed << std::setprecision(3) << story_cfg.S << "\n";
                    std::cout << "  OOS net profit=" << wf_summary.net_profit
                              << " net maxDD=" << wf_summary.net_max_dd
                              << " turnover contracts=" << wf_summary.turnover_contracts << "\n";
                    std::cout << "  Full-sample net profit=" << full_summary.net_profit
                              << " net maxDD=" << full_summary.net_max_dd << "\n";
                }
            }

            if (options.mode == "both" || options.mode == "reference") {
                ReferenceBundle reference = run_reference_split(bars, spec, options, options.verbose);
                write_reference_config_csv(
                    market_dir / (spec.ticker + "_tf_reference_config.csv"),
                    reference.config,
                    reference.best_params
                );
                write_reference_surface_csv(
                    market_dir / (spec.ticker + "_tf_reference_surface.csv"),
                    reference.surface
                );
                write_series_csv(
                    market_dir / (spec.ticker + "_tf_reference_series.csv"),
                    reference.series_rows
                );
                write_trades_csv(
                    market_dir / (spec.ticker + "_tf_reference_trades.csv"),
                    reference.trades
                );
                write_summary_csv(
                    market_dir / (spec.ticker + "_tf_reference_summary.csv"),
                    reference.summaries
                );
                for (const SummaryRow& row : reference.summaries) {
                    all_summaries.push_back(row);
                }
            }
        }

        write_summary_csv(options.out_dir / "tf_backtest_summary.csv", all_summaries);
        if (options.verbose) {
            std::cout << "\nWrote CSV outputs to " << options.out_dir << "\n";
        }
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "Error: " << exc.what() << "\n";
        return 1;
    }
}
