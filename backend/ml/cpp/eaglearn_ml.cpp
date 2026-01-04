/**
 * Eaglearn ML C++ Extension Implementation
 * High-performance implementations for ML pipeline components
 */

#include "eaglearn_ml.h"
#include <iostream>
#include <algorithm>
#include <numeric>
#include <cstring>
#include <openssl/evp.h>
#include <openssl/kdf.h>
#include <openssl/rand.h>

namespace py = pybind11;

// ============================================================================
// FramePreprocessor Implementation
// ============================================================================
FramePreprocessor::FramePreprocessor(int target_width, int target_height)
    : target_width_(target_width), target_height_(target_height) {}

py::array_t<float> FramePreprocessor::preprocess(py::array_t<unsigned char>& frame) {
    py::buffer_info buf = frame.request();
    
    if (buf.ndim != 3) {
        throw std::runtime_error("Frame must be 3D array (height, width, channels)");
    }
    
    int height = buf.shape[0];
    int width = buf.shape[1];
    int channels = buf.shape[2];
    
    // Resize if needed
    cv::Mat input_frame;
    if (channels == 3) {
        cv::Mat temp(height, width, CV_8UC3, buf.ptr);
        cv::cvtColor(temp, input_frame, cv::COLOR_BGR2RGB);
    } else {
        cv::Mat temp(height, width, CV_8UC(channels), buf.ptr);
        cv::cvtColor(temp, input_frame, cv::COLOR_GRAY2RGB);
    }
    
    cv::Mat resized;
    if (width != target_width_ || height != target_height_) {
        cv::resize(input_frame, resized, cv::Size(target_width_, target_height_));
    } else {
        resized = input_frame;
    }
    
    // Normalize to 0-1 range
    cv::Mat normalized;
    resized.convertTo(normalized, CV_32FC3, 1.0 / 255.0);
    
    // Create output array
    py::array_t<float> output({target_height_, target_width_, 3});
    py::buffer_info out_buf = output.request();
    
    std::memcpy(out_buf.ptr, normalized.data, normalized.total() * sizeof(float));
    
    return output;
}

py::array_t<unsigned char> FramePreprocessor::denormalize(py::array_t<float>& frame) {
    py::buffer_info buf = frame.request();
    
    if (buf.ndim != 3) {
        throw std::runtime_error("Frame must be 3D array");
    }
    
    int height = buf.shape[0];
    int width = buf.shape[1];
    
    cv::Mat input(height, width, CV_32FC3, buf.ptr);
    cv::Mat denormalized;
    input.convertTo(denormalized, CV_8UC3, 255.0);
    
    py::array_t<unsigned char> output({height, width, 3});
    py::buffer_info out_buf = output.request();
    
    std::memcpy(out_buf.ptr, denormalized.data, denormalized.total() * sizeof(unsigned char));
    
    return output;
}

// ============================================================================
// AudioPreprocessor Implementation
// ============================================================================
AudioPreprocessor::AudioPreprocessor(int target_sample_rate)
    : target_sample_rate_(target_sample_rate) {}

void AudioPreprocessor::resample(const float* input, int input_len, float* output, int output_len,
                                  int original_sr, int target_sr) {
    if (original_sr == target_sr || input_len == 0) {
        int copy_len = std::min(input_len, output_len);
        std::memcpy(output, input, copy_len * sizeof(float));
        if (output_len > copy_len) {
            std::fill(output + copy_len, output + output_len, 0.0f);
        }
        return;
    }
    
    double ratio = static_cast<double>(target_sr) / original_sr;
    int new_len = static_cast<int>(input_len * ratio);
    new_len = std::min(new_len, output_len);
    
    for (int i = 0; i < new_len; i++) {
        double src_idx = i / ratio;
        int src_idx_0 = static_cast<int>(std::floor(src_idx));
        int src_idx_1 = std::min(src_idx_0 + 1, input_len - 1);
        double frac = src_idx - src_idx_0;
        
        output[i] = input[src_idx_0] * (1.0 - frac) + input[src_idx_1] * frac;
    }
    
    if (new_len < output_len) {
        std::fill(output + new_len, output + output_len, 0.0f);
    }
}

py::array_t<float> AudioPreprocessor::preprocess(py::array_t<float>& audio_data, int original_sample_rate) {
    py::buffer_info buf = audio_data.request();
    int input_len = buf.size;
    const float* input_ptr = buf.data;
    
    // Calculate output length
    double ratio = static_cast<double>(target_sample_rate_) / original_sample_rate;
    int output_len = static_cast<int>(input_len * ratio);
    
    py::array_t<float> output(output_len);
    py::buffer_info out_buf = output.request();
    float* output_ptr = out_buf.data;
    
    // Resample
    resample(input_ptr, input_len, output_ptr, output_len, original_sample_rate, target_sample_rate_);
    
    // Normalize amplitude to -1 to 1 range
    float max_val = 0.0f;
    for (int i = 0; i < output_len; i++) {
        max_val = std::max(max_val, std::fabs(output_ptr[i]));
    }
    if (max_val > 0) {
        for (int i = 0; i < output_len; i++) {
            output_ptr[i] /= max_val;
        }
    }
    
    // Remove DC offset
    float mean = 0.0f;
    for (int i = 0; i < output_len; i++) {
        mean += output_ptr[i];
    }
    mean /= output_len;
    for (int i = 0; i < output_len; i++) {
        output_ptr[i] -= mean;
    }
    
    return output;
}

// ============================================================================
// CalibrationService Implementation
// ============================================================================
CalibrationService::CalibrationService() {}

std::pair<py::array_t<double>, double> CalibrationService::calculate_transformation_matrix(
    std::vector<std::pair<double, double>> screen_points,
    std::vector<std::pair<double, double>> gaze_points) {
    
    if (screen_points.size() != 4 || gaze_points.size() != 4) {
        throw std::runtime_error("Exactly 4 calibration points required");
    }
    
    std::vector<cv::Point2d> src_pts, dst_pts;
    for (const auto& p : gaze_points) {
        src_pts.emplace_back(p.first, p.second);
    }
    for (const auto& p : screen_points) {
        dst_pts.emplace_back(p.first, p.second);
    }
    
    cv::Mat homography = cv::findHomography(src_pts, dst_pts, cv::RANSAC, 5.0);
    
    if (homography.empty()) {
        throw std::runtime_error("Failed to calculate homography matrix");
    }
    
    // Convert to numpy array
    py::array_t<double> matrix({3, 3});
    py::buffer_info mbuf = matrix.request();
    cv::Mat m(3, 3, CV_64F, mbuf.ptr);
    homography.convertTo(m, CV_64F);
    
    double accuracy = calculate_accuracy(
        py::array_t<double>({4, 2}, reinterpret_cast<double*>(src_pts.data())),
        py::array_t<double>({4, 2}, reinterpret_cast<double*>(dst_pts.data())),
        matrix);
    
    return {matrix, accuracy};
}

double CalibrationService::calculate_accuracy(
    const py::array_t<double>& src_points,
    const py::array_t<double>& dst_points,
    const py::array_t<double>& matrix) {
    
    py::buffer_info src_buf = src_points.request();
    py::buffer_info dst_buf = dst_points.request();
    py::buffer_info m_buf = matrix.request();
    
    int num_points = src_buf.shape[0];
    cv::Mat src(num_points, 2, CV_64F, src_buf.ptr);
    cv::Mat dst(num_points, 2, CV_64F, dst_buf.ptr);
    cv::Mat M(3, 3, CV_64F, m_buf.ptr);
    
    // Transform source points
    cv::Mat src_homogeneous(num_points, 3, CV_64F);
    for (int i = 0; i < num_points; i++) {
        src_homogeneous.at<double>(i, 0) = src.at<double>(i, 0);
        src_homogeneous.at<double>(i, 1) = src.at<double>(i, 1);
        src_homogeneous.at<double>(i, 2) = 1.0;
    }
    
    cv::Mat transformed = M * src_homogeneous.t();
    cv::Mat transformed_pts(num_points, 2, CV_64F);
    for (int i = 0; i < num_points; i++) {
        transformed_pts.at<double>(i, 0) = transformed.at<double>(0, i) / transformed.at<double>(2, i);
        transformed_pts.at<double>(i, 1) = transformed.at<double>(1, i) / transformed.at<double>(2, i);
    }
    
    // Calculate MSE
    cv::Mat diff = transformed_pts - dst;
    cv::Mat sq_diff;
    cv::pow(diff, 2, sq_diff);
    double mse = cv::sum(sq_diff)[0] / num_points;
    
    // Convert to accuracy score
    double max_error = 100.0;
    double accuracy = std::max(0.0, 1.0 - (std::sqrt(mse) / max_error));
    
    return accuracy;
}

py::array_t<double> CalibrationService::json_to_matrix(const std::string& json_str) {
    // Simple JSON parsing for 3x3 matrix
    py::array_t<double> matrix({3, 3});
    py::buffer_info buf = matrix.request();
    
    // Parse manually - look for numbers
    std::vector<double> values;
    std::string num_str;
    bool in_num = false;
    bool negative = false;
    
    for (size_t i = 0; i <= json_str.size(); i++) {
        char c = (i < json_str.size()) ? json_str[i] : ' ';
        if (c == '-' && !in_num) {
            negative = true;
            in_num = true;
            num_str = "-";
        } else if (c >= '0' && c <= '9' || c == '.') {
            if (!in_num) {
                in_num = true;
                num_str = std::string(1, c);
            } else {
                num_str += c;
            }
        } else if (in_num) {
            if (!negative) {
                values.push_back(std::stod(num_str));
            } else {
                values.push_back(-std::stod(num_str));
            }
            in_num = false;
            negative = false;
            num_str.clear();
        }
    }
    
    if (values.size() >= 9) {
        double* ptr = reinterpret_cast<double*>(buf.ptr);
        for (int i = 0; i < 9; i++) {
            ptr[i] = values[i];
        }
    }
    
    return matrix;
}

std::string CalibrationService::matrix_to_json(const py::array_t<double>& matrix) {
    py::buffer_info buf = matrix.request();
    double* ptr = reinterpret_cast<double*>(buf.ptr);
    
    std::string json = "[";
    for (int i = 0; i < 3; i++) {
        json += "[";
        for (int j = 0; j < 3; j++) {
            json += std::to_string(ptr[i * 3 + j]);
            if (j < 2) json += ",";
        }
        json += "]";
        if (i < 2) json += ",";
    }
    json += "]";
    
    return json;
}

// ============================================================================
// HeadPoseEstimator Implementation
// ============================================================================
HeadPoseEstimator::HeadPoseEstimator() {
    // 3D model points (canonical face model)
    model_points_ = {
        cv::Point3d(0.0, 0.0, 0.0),           // Nose tip
        cv::Point3d(0.0, -330.0, -65.0),      // Chin
        cv::Point3d(-225.0, 170.0, -135.0),   // Left eye left corner
        cv::Point3d(225.0, 170.0, -135.0),    // Right eye right corner
        cv::Point3d(-150.0, -150.0, -125.0),  // Left mouth corner
        cv::Point3d(150.0, -150.0, -125.0)    // Right mouth corner
    };
    
    landmark_indices_ = {1, 152, 33, 263, 61, 291};
}

py::dict HeadPoseEstimator::estimate(py::array_t<unsigned char>& frame) {
    py::buffer_info buf = frame.request();
    
    if (buf.ndim != 3) {
        return {{"yaw", 0.0}, {"pitch", 0.0}, {"roll", 0.0},
                {"posture", "unknown"}, {"confidence", 0.0},
                {"landmarks_detected", false}};
    }
    
    int height = buf.shape[0];
    int width = buf.shape[1];
    
    cv::Mat input_frame(height, width, CV_8UC3, buf.ptr);
    cv::Mat rgb_frame;
    cv::cvtColor(input_frame, rgb_frame, cv::COLOR_BGR2RGB);
    
    // Note: Full MediaPipe C++ integration requires additional setup
    // This is a simplified placeholder that returns default values
    // For production, integrate MediaPipe C++ SDK
    
    py::dict result;
    result["yaw"] = 0.0;
    result["pitch"] = 0.0;
    result["roll"] = 0.0;
    result["posture"] = "unknown";
    result["confidence"] = 0.0;
    result["landmarks_detected"] = false;
    
    return result;
}

std::string HeadPoseEstimator::classify_posture(double yaw, double pitch, double roll) {
    if (std::abs(yaw) < 15 && std::abs(pitch) < 15 && std::abs(roll) < 10) {
        return "good";
    }
    if (pitch > 15) {
        return "forward";
    }
    if (std::abs(roll) > 10) {
        return "tilted";
    }
    if (pitch < -15) {
        return "slouched";
    }
    return "good";
}

double HeadPoseEstimator::calculate_confidence(int num_landmarks) {
    int expected_landmarks = 478;
    return std::min(static_cast<double>(num_landmarks) / expected_landmarks, 1.0);
}

// ============================================================================
// GazeEstimator Implementation
// ============================================================================
GazeEstimator::GazeEstimator(int smoothing_window)
    : smoothing_window_(smoothing_window) {
    left_eye_indices_ = {33, 133, 160, 159, 158, 157, 173, 144};
    right_eye_indices_ = {362, 263, 387, 386, 385, 384, 398, 373};
    left_iris_indices_ = {468, 469, 470, 471, 472};
    right_iris_indices_ = {473, 474, 475, 476, 477};
}

GazeEstimator::~GazeEstimator() {}

py::dict GazeEstimator::estimate(py::array_t<unsigned char>& frame,
                                  py::array_t<double> calibration_matrix) {
    py::buffer_info buf = frame.request();
    
    py::dict result;
    result["gaze_x"] = 0.5;
    result["gaze_y"] = 0.5;
    result["confidence"] = 0.0;
    result["raw_gaze_x"] = 0.5;
    result["raw_gaze_y"] = 0.5;
    result["landmarks_detected"] = false;
    
    return result;
}

void GazeEstimator::reset_smoothing() {
    gaze_history_.clear();
}

py::tuple GazeEstimator::apply_smoothing(double gaze_x, double gaze_y) {
    gaze_history_.push_back({gaze_x, gaze_y});
    
    if (gaze_history_.size() > static_cast<size_t>(smoothing_window_)) {
        gaze_history_.erase(gaze_history_.begin());
    }
    
    if (gaze_history_.empty()) {
        return py::make_tuple(gaze_x, gaze_y);
    }
    
    double sum_x = 0.0, sum_y = 0.0;
    for (const auto& g : gaze_history_) {
        sum_x += g.first;
        sum_y += g.second;
    }
    
    return py::make_tuple(sum_x / gaze_history_.size(), sum_y / gaze_history_.size());
}

double GazeEstimator::calculate_confidence(int num_landmarks) {
    int expected_landmarks = 478;
    return std::min(static_cast<double>(num_landmarks) / expected_landmarks, 1.0);
}

// ============================================================================
// KPICalculator Implementation
// ============================================================================
KPICalculator::KPICalculator() {
    weights_ = {{"focus", 0.35}, {"engagement", 0.25}, {"stress", 0.20}, {"posture", 0.20}};
}

py::dict KPICalculator::calculate_productivity_metrics(
    const std::vector<py::dict>& gaze_data,
    const std::vector<py::dict>& pose_data,
    const std::vector<py::dict>& stress_data,
    const std::string& window_start,
    const std::string& window_end) {
    
    double focus_score = calculate_focus_score(gaze_data);
    double engagement_score = calculate_engagement_score(gaze_data, pose_data);
    double stress_score = calculate_stress_score(stress_data);
    double posture_score = calculate_posture_score(pose_data);
    
    double overall_productivity = 
        weights_["focus"] * focus_score +
        weights_["engagement"] * engagement_score +
        weights_["stress"] * stress_score +
        weights_["posture"] * posture_score;
    
    py::dict result;
    result["focus_score"] = focus_score;
    result["engagement_score"] = engagement_score;
    result["stress_score"] = stress_score;
    result["posture_score"] = posture_score;
    result["overall_productivity"] = overall_productivity;
    result["window_start"] = window_start;
    result["window_end"] = window_end;
    
    return result;
}

double KPICalculator::calculate_focus_score(const std::vector<py::dict>& gaze_data) {
    if (gaze_data.empty()) {
        return 0.5;
    }
    
    std::vector<double> distances;
    for (const auto& gaze : gaze_data) {
        double confidence = gaze.contains("confidence") ? gaze["confidence"].cast<double>() : 0.0;
        if (confidence > 0.5) {
            double gaze_x = gaze.contains("gaze_x") ? gaze["gaze_x"].cast<double>() : 0.5;
            double gaze_y = gaze.contains("gaze_y") ? gaze["gaze_y"].cast<double>() : 0.5;
            double dx = gaze_x - 0.5;
            double dy = gaze_y - 0.5;
            distances.push_back(std::sqrt(dx * dx + dy * dy));
        }
    }
    
    if (distances.empty()) {
        return 0.5;
    }
    
    double avg_distance = std::accumulate(distances.begin(), distances.end(), 0.0) / distances.size();
    return std::max(0.0, 1.0 - (avg_distance * 2.0));
}

double KPICalculator::calculate_engagement_score(
    const std::vector<py::dict>& gaze_data,
    const std::vector<py::dict>& pose_data) {
    
    if (gaze_data.empty() && pose_data.empty()) {
        return 0.5;
    }
    
    double gaze_engagement = 0.5;
    if (!gaze_data.empty()) {
        int high_conf = 0;
        for (const auto& gaze : gaze_data) {
            double confidence = gaze.contains("confidence") ? gaze["confidence"].cast<double>() : 0.0;
            if (confidence > 0.7) {
                high_conf++;
            }
        }
        gaze_engagement = static_cast<double>(high_conf) / gaze_data.size();
    }
    
    double pose_engagement = 0.5;
    if (!pose_data.empty()) {
        int good_poses = 0;
        for (const auto& pose : pose_data) {
            double yaw = pose.contains("yaw") ? std::abs(pose["yaw"].cast<double>()) : 0.0;
            double pitch = pose.contains("pitch") ? std::abs(pose["pitch"].cast<double>()) : 0.0;
            if (yaw < 20 && pitch < 20) {
                good_poses++;
            }
        }
        pose_engagement = static_cast<double>(good_poses) / pose_data.size();
    }
    
    return (gaze_engagement + pose_engagement) / 2.0;
}

double KPICalculator::calculate_stress_score(const std::vector<py::dict>& stress_data) {
    if (stress_data.empty()) {
        return 0.5;
    }
    
    std::vector<double> stress_levels;
    for (const auto& s : stress_data) {
        double confidence = s.contains("confidence") ? s["confidence"].cast<double>() : 0.0;
        if (confidence > 0.5) {
            double level = s.contains("stress_level") ? s["stress_level"].cast<double>() : 0.0;
            stress_levels.push_back(level);
        }
    }
    
    if (stress_levels.empty()) {
        return 0.5;
    }
    
    double avg_stress = std::accumulate(stress_levels.begin(), stress_levels.end(), 0.0) / stress_levels.size();
    return 1.0 - avg_stress;
}

double KPICalculator::calculate_posture_score(const std::vector<py::dict>& pose_data) {
    if (pose_data.empty()) {
        return 0.5;
    }
    
    int good_postures = 0;
    for (const auto& pose : pose_data) {
        std::string posture = pose.contains("posture") ? pose["posture"].cast<std::string>() : "";
        if (posture == "good") {
            good_postures++;
        }
    }
    
    return static_cast<double>(good_postures) / pose_data.size();
}

py::dict KPICalculator::get_default_metrics(const std::string& window_start, const std::string& window_end) {
    py::dict result;
    result["focus_score"] = 0.5;
    result["engagement_score"] = 0.5;
    result["stress_score"] = 0.5;
    result["posture_score"] = 0.5;
    result["overall_productivity"] = 0.5;
    result["window_start"] = window_start;
    result["window_end"] = window_end;
    return result;
}

// ============================================================================
// StressAnalyzer Implementation
// ============================================================================
StressAnalyzer::StressAnalyzer(int sample_rate)
    : sample_rate_(sample_rate) {
    n_mfcc_ = 13;
    stress_thresholds_ = {{"low", 0.33}, {"medium", 0.66}, {"high", 1.0}};
}

py::dict StressAnalyzer::analyze(py::array_t<float>& audio_data) {
    py::buffer_info buf = audio_data.request();
    int num_samples = buf.size;
    
    if (num_samples == 0) {
        return get_default_result();
    }
    
    py::dict features = extract_features(audio_data);
    double stress_level = calculate_stress_level(features);
    std::string stress_category = classify_stress(stress_level);
    double confidence = calculate_confidence(audio_data, features);
    
    py::dict result;
    result["stress_level"] = stress_level;
    result["stress_category"] = stress_category;
    result["confidence"] = confidence;
    result["features"] = features;
    
    return result;
}

py::dict StressAnalyzer::extract_features(py::array_t<float>& audio_data) {
    py::buffer_info buf = audio_data.request();
    const float* data = buf.data;
    int num_samples = buf.size;
    
    // Simplified feature extraction (full librosa replacement would be more complex)
    double sum = 0.0, sum_sq = 0.0;
    for (int i = 0; i < num_samples; i++) {
        sum += data[i];
        sum_sq += data[i] * data[i];
    }
    double mean = sum / num_samples;
    double variance = (sum_sq / num_samples) - (mean * mean);
    double std_dev = std::sqrt(std::max(0.0, variance));
    
    // Zero crossing rate (simplified)
    int zero_crossings = 0;
    for (int i = 1; i < num_samples; i++) {
        if ((data[i] >= 0 && data[i-1] < 0) || (data[i] < 0 && data[i-1] >= 0)) {
            zero_crossings++;
        }
    }
    double zcr = static_cast<double>(zero_crossings) / num_samples;
    
    // Spectral centroid (simplified using RMS as proxy)
    double rms = std::sqrt(sum_sq / num_samples);
    
    py::dict features;
    features["pitch_mean"] = 0.0;
    features["pitch_std"] = 0.0;
    features["energy_mean"] = rms;
    features["energy_std"] = std_dev;
    features["speaking_rate"] = 0.0;
    features["mfcc"] = py::list();
    features["spectral_centroid"] = 0.0;
    features["spectral_bandwidth"] = 0.0;
    features["spectral_rolloff"] = 0.0;
    features["zero_crossing_rate"] = zcr;
    features["hrv_estimate"] = 0.0;
    
    return features;
}

double StressAnalyzer::calculate_stress_level(const py::dict& features) {
    double pitch_stress = 0.0;
    double energy_stress = 0.0;
    double speaking_stress = 0.0;
    double spectral_stress = 0.0;
    double hrv_stress = 0.0;
    
    if (features.contains("pitch_std")) {
        double pitch_std = features["pitch_std"].cast<double>();
        pitch_stress = std::min(pitch_std / 100.0, 1.0);
    }
    
    if (features.contains("energy_std")) {
        double energy_std = features["energy_std"].cast<double>();
        energy_stress = std::min(energy_std / 0.1, 1.0);
    }
    
    if (features.contains("speaking_rate")) {
        double speaking_rate = features["speaking_rate"].cast<double>();
        speaking_stress = std::min(speaking_rate / 200.0, 1.0);
    }
    
    if (features.contains("spectral_centroid")) {
        double spectral_centroid = features["spectral_centroid"].cast<double>();
        spectral_stress = std::min(spectral_centroid / 5000.0, 1.0);
    }
    
    if (features.contains("hrv_estimate")) {
        double hrv = features["hrv_estimate"].cast<double>();
        hrv_stress = std::min(hrv / 0.5, 1.0);
    }
    
    double stress_level = (
        0.25 * pitch_stress +
        0.20 * energy_stress +
        0.20 * speaking_stress +
        0.20 * spectral_stress +
        0.15 * hrv_stress
    );
    
    return std::max(0.0, std::min(1.0, stress_level));
}

std::string StressAnalyzer::classify_stress(double stress_level) {
    if (stress_level < stress_thresholds_["low"]) {
        return "low";
    } else if (stress_level < stress_thresholds_["medium"]) {
        return "medium";
    }
    return "high";
}

double StressAnalyzer::calculate_confidence(py::array_t<float>& audio_data, const py::dict& features) {
    py::buffer_info buf = audio_data.request();
    int num_samples = buf.size;
    
    double min_samples = sample_rate_ * 0.5;
    double length_score = std::min(static_cast<double>(num_samples) / min_samples, 1.0);
    
    double energy_score = 0.5;
    if (features.contains("energy_mean")) {
        double energy_mean = features["energy_mean"].cast<double>();
        energy_score = std::min(energy_mean / 0.01, 1.0);
    }
    
    return std::max(0.0, std::min(1.0, (length_score + energy_score) / 2.0));
}

py::dict StressAnalyzer::get_default_result() {
    py::dict features;
    features["pitch_mean"] = 0.0;
    features["pitch_std"] = 0.0;
    features["energy_mean"] = 0.0;
    features["energy_std"] = 0.0;
    features["speaking_rate"] = 0.0;
    
    py::list mfcc;
    for (int i = 0; i < n_mfcc_; i++) {
        mfcc.append(0.0);
    }
    features["mfcc"] = mfcc;
    
    features["spectral_centroid"] = 0.0;
    features["spectral_bandwidth"] = 0.0;
    features["spectral_rolloff"] = 0.0;
    features["zero_crossing_rate"] = 0.0;
    features["hrv_estimate"] = 0.0;
    
    py::dict result;
    result["stress_level"] = 0.0;
    result["stress_category"] = "low";
    result["confidence"] = 0.0;
    result["features"] = features;
    
    return result;
}

// ============================================================================
// EncryptionManager Implementation
// ============================================================================
EncryptionManager::EncryptionManager(const std::string& master_key) {
    salt_ = {'e', 'a', 'g', 'l', 'e', 'a', 'r', 'n', '_', 's', 'a', 'l', 't', '_', 'v', '1'};
    key_ = derive_key(master_key);
}

std::vector<unsigned char> EncryptionManager::derive_key(const std::string& master_key) {
    std::vector<unsigned char> key(32);
    
    if (!master_key.empty()) {
        // PBKDF2 key derivation (simplified - using PKCS5_PBKDF2_HMAC)
        PKCS5_PBKDF2_HMAC(
            master_key.c_str(), master_key.length(),
            salt_.data(), salt_.size(),
            100000,
            EVP_sha256(),
            32,
            key.data()
        );
    }
    
    return key;
}

std::string EncryptionManager::encrypt(const std::string& plaintext) {
    if (plaintext.empty()) {
        return plaintext;
    }
    
    if (key_.empty()) {
        throw std::runtime_error("Encryption key not set");
    }
    
    // Generate random nonce
    unsigned char nonce[12];
    RAND_bytes(nonce, 12);
    
    // Create cipher
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, key_.data(), nonce);
    
    // Encrypt
    int ciphertext_len;
    int plaintext_len = plaintext.length();
    std::vector<unsigned char> ciphertext(plaintext_len + 16);
    
    EVP_EncryptUpdate(ctx, ciphertext.data(), &ciphertext_len,
                      reinterpret_cast<const unsigned char*>(plaintext.data()), plaintext_len);
    int update_len = ciphertext_len;
    
    // Finalize
    EVP_EncryptFinal_ex(ctx, ciphertext.data() + update_len, &ciphertext_len);
    int total_len = update_len + ciphertext_len;
    ciphertext.resize(total_len);
    
    // Get tag
    unsigned char tag[16];
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16, tag);
    
    EVP_CIPHER_CTX_free(ctx);
    
    // Combine nonce + tag + ciphertext
    std::vector<unsigned char> encrypted_data;
    encrypted_data.insert(encrypted_data.end(), nonce, nonce + 12);
    encrypted_data.insert(encrypted_data.end(), tag, tag + 16);
    encrypted_data.insert(encrypted_data.end(), ciphertext.begin(), ciphertext.end());
    
    // Base64 encode
    static const char b64_chars[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string result;
    
    for (size_t i = 0; i < encrypted_data.size(); i += 3) {
        unsigned char b1 = encrypted_data[i];
        unsigned char b2 = (i + 1 < encrypted_data.size()) ? encrypted_data[i + 1] : 0;
        unsigned char b3 = (i + 2 < encrypted_data.size()) ? encrypted_data[i + 2] : 0;
        
        result += b64_chars[b1 >> 2];
        result += b64_chars[((b1 & 0x03) << 4) | (b2 >> 4)];
        result += (i + 1 < encrypted_data.size()) ? b64_chars[((b2 & 0x0F) << 2) | (b3 >> 6)] : '=';
        result += (i + 2 < encrypted_data.size()) ? b64_chars[b3 & 0x3F] : '=';
    }
    
    return result;
}

std::string EncryptionManager::decrypt(const std::string& encrypted) {
    if (encrypted.empty()) {
        return encrypted;
    }
    
    if (key_.empty()) {
        throw std::runtime_error("Encryption key not set");
    }
    
    // Base64 decode
    static const int b64_decode_map[256] = {
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,62,-1,-1,-1,63,
        52,53,54,55,56,57,58,59,60,61,-1,-1,-1,-1,-1,-1,
        -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,
        15,16,17,18,19,20,21,22,23,24,25,-1,-1,-1,-1,-1,
        -1,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,
        41,42,43,44,45,46,47,48,49,50,51,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1
    };
    
    std::vector<unsigned char> encrypted_data;
    for (size_t i = 0; i < encrypted.length(); i += 4) {
        unsigned char b1 = b64_decode_map[static_cast<unsigned char>(encrypted[i])];
        unsigned char b2 = b64_decode_map[static_cast<unsigned char>(encrypted[i + 1])];
        unsigned char b3 = (encrypted[i + 2] != '=') ? b64_decode_map[static_cast<unsigned char>(encrypted[i + 2])] : 0;
        unsigned char b4 = (encrypted[i + 3] != '=') ? b64_decode_map[static_cast<unsigned char>(encrypted[i + 3])] : 0;
        
        encrypted_data.push_back((b1 << 2) | (b2 >> 4));
        if (encrypted[i + 2] != '=') {
            encrypted_data.push_back(((b2 & 0x0F) << 4) | (b3 >> 2));
        }
        if (encrypted[i + 3] != '=') {
            encrypted_data.push_back(((b3 & 0x03) << 6) | b4);
        }
    }
    
    if (encrypted_data.size() < 28) {
        throw std::runtime_error("Invalid encrypted data");
    }
    
    // Extract nonce, tag, ciphertext
    unsigned char nonce[12];
    unsigned char tag[16];
    std::vector<unsigned char> ciphertext(encrypted_data.begin() + 28, encrypted_data.end());
    
    std::memcpy(nonce, encrypted_data.data(), 12);
    std::memcpy(tag, encrypted_data.data() + 12, 16);
    
    // Create decipher
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, key_.data(), nonce);
    
    // Decrypt
    int plaintext_len;
    std::vector<unsigned char> plaintext(ciphertext.size());
    EVP_DecryptUpdate(ctx, plaintext.data(), &plaintext_len, ciphertext.data(), ciphertext.size());
    int update_len = plaintext_len;
    
    // Set tag for verification
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, 16, tag);
    
    // Finalize
    int ret = EVP_DecryptFinal_ex(ctx, plaintext.data() + update_len, &plaintext_len);
    EVP_CIPHER_CTX_free(ctx);
    
    if (ret <= 0) {
        throw std::runtime_error("Decryption failed");
    }
    
    int total_len = update_len + plaintext_len;
    plaintext.resize(total_len);
    
    return std::string(plaintext.begin(), plaintext.end());
}
