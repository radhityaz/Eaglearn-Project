/**
 * Eaglearn ML C++ Extension Header
 * High-performance implementations for ML pipeline components
 */

#ifndef EAGLEARN_ML_H
#define EAGLEARN_ML_H

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <opencv2/opencv.hpp>
#include <vector>
#include <string>
#include <memory>
#include <cmath>

namespace py = pybind11;

// ============================================================================
// FramePreprocessor - Video frame preprocessing
// ============================================================================
class FramePreprocessor {
public:
    FramePreprocessor(int target_width = 640, int target_height = 480);
    py::array_t<float> preprocess(py::array_t<unsigned char>& frame);
    py::array_t<unsigned char> denormalize(py::array_t<float>& frame);
    
private:
    int target_width_;
    int target_height_;
};

// ============================================================================
// AudioPreprocessor - Audio preprocessing for stress analysis
// ============================================================================
class AudioPreprocessor {
public:
    AudioPreprocessor(int target_sample_rate = 16000);
    py::array_t<float> preprocess(py::array_t<float>& audio_data, int original_sample_rate);
    
private:
    int target_sample_rate_;
    
    void resample(const float* input, int input_len, float* output, int output_len, 
                  int original_sr, int target_sr);
};

// ============================================================================
// CalibrationService - Gaze calibration using homography
// ============================================================================
class CalibrationService {
public:
    CalibrationService();
    std::pair<py::array_t<double>, double> calculate_transformation_matrix(
        std::vector<std::pair<double, double>> screen_points,
        std::vector<std::pair<double, double>> gaze_points);
    py::array_t<double> json_to_matrix(const std::string& json_str);
    std::string matrix_to_json(const py::array_t<double>& matrix);
    
private:
    double calculate_accuracy(
        const py::array_t<double>& src_points,
        const py::array_t<double>& dst_points,
        const py::array_t<double>& matrix);
};

// ============================================================================
// HeadPoseEstimator - Head pose estimation (simplified C++ version)
// Note: Full MediaPipe C++ binding is complex, providing lightweight version
// ============================================================================
class HeadPoseEstimator {
public:
    HeadPoseEstimator();
    py::dict estimate(py::array_t<unsigned char>& frame);
    
    struct PoseResult {
        double yaw;
        double pitch;
        double roll;
        std::string posture;
        double confidence;
        bool landmarks_detected;
    };
    
private:
    PoseResult estimate_pose(cv::Mat& frame);
    std::pair<py::array_t<double>, py::array_t<double>> extract_2d_points(
        const std::vector<cv::Point2f>& landmarks, 
        int width, int height);
    py::tuple calculate_pose_angles(
        const py::array_t<double>& image_points,
        int width, int height);
    py::tuple rotation_matrix_to_euler_angles(const cv::Mat& R);
    std::string classify_posture(double yaw, double pitch, double roll);
    double calculate_confidence(int num_landmarks);
    
    // 3D model points (canonical face model)
    std::vector<cv::Point3d> model_points_;
    std::vector<int> landmark_indices_;
};

// ============================================================================
// GazeEstimator - Gaze estimation (simplified C++ version)
// ============================================================================
class GazeEstimator {
public:
    GazeEstimator(int smoothing_window = 5);
    ~GazeEstimator();
    py::dict estimate(py::array_t<unsigned char>& frame, 
                     py::array_t<double> calibration_matrix = py::none());
    void reset_smoothing();
    
private:
    py::tuple calculate_gaze_from_landmarks(
        const std::vector<cv::Point2f>& landmarks,
        int width, int height);
    py::tuple apply_calibration(double gaze_x, double gaze_y,
                                const py::array_t<double>& calibration_matrix);
    py::tuple apply_smoothing(double gaze_x, double gaze_y);
    double calculate_confidence(int num_landmarks);
    
    int smoothing_window_;
    std::vector<std::pair<double, double>> gaze_history_;
    std::vector<int> left_eye_indices_;
    std::vector<int> right_eye_indices_;
    std::vector<int> left_iris_indices_;
    std::vector<int> right_iris_indices_;
};

// ============================================================================
// KPICalculator - Productivity KPI calculations
// ============================================================================
class KPICalculator {
public:
    KPICalculator();
    py::dict calculate_productivity_metrics(
        const std::vector<py::dict>& gaze_data,
        const std::vector<py::dict>& pose_data,
        const std::vector<py::dict>& stress_data,
        const std::string& window_start,
        const std::string& window_end);
    
private:
    double calculate_focus_score(const std::vector<py::dict>& gaze_data);
    double calculate_engagement_score(
        const std::vector<py::dict>& gaze_data,
        const std::vector<py::dict>& pose_data);
    double calculate_stress_score(const std::vector<py::dict>& stress_data);
    double calculate_posture_score(const std::vector<py::dict>& pose_data);
    py::dict get_default_metrics(const std::string& window_start, const std::string& window_end);
    
    std::map<std::string, double> weights_;
};

// ============================================================================
// StressAnalyzer - Audio stress analysis (simplified)
// Note: Full librosa replacement requires aubio or similar
// ============================================================================
class StressAnalyzer {
public:
    StressAnalyzer(int sample_rate = 16000);
    py::dict analyze(py::array_t<float>& audio_data);
    
private:
    py::dict extract_features(py::array_t<float>& audio_data);
    double calculate_stress_level(const py::dict& features);
    std::string classify_stress(double stress_level);
    double calculate_confidence(py::array_t<float>& audio_data, const py::dict& features);
    py::dict get_default_result();
    
    int sample_rate_;
    int n_mfcc_;
    std::map<std::string, double> stress_thresholds_;
};

// ============================================================================
// EncryptionManager - AES-256-GCM encryption
// Note: Using OpenSSL C++ wrapper
// ============================================================================
class EncryptionManager {
public:
    EncryptionManager(const std::string& master_key = "");
    std::string encrypt(const std::string& plaintext);
    std::string decrypt(const std::string& encrypted);
    
private:
    std::vector<unsigned char> derive_key(const std::string& master_key);
    
    std::vector<unsigned char> key_;
    std::vector<unsigned char> salt_;
};

// ============================================================================
// Module initialization
// ============================================================================
PYBIND11_MODULE(eaglearn_ml, m) {
    m.doc() = "Eaglearn ML C++ Extension - High performance ML components";
    
    // FramePreprocessor
    py::class_<FramePreprocessor>(m, "FramePreprocessor")
        .def(py::init<int, int>(), py::arg("target_width") = 640, py::arg("target_height") = 480)
        .def("preprocess", &FramePreprocessor::preprocess)
        .def("denormalize", &FramePreprocessor::denormalize);
    
    // AudioPreprocessor
    py::class_<AudioPreprocessor>(m, "AudioPreprocessor")
        .def(py::init<int>(), py::arg("target_sample_rate") = 16000)
        .def("preprocess", &AudioPreprocessor::preprocess);
    
    // CalibrationService
    py::class_<CalibrationService>(m, "CalibrationService")
        .def(py::init<>())
        .def("calculate_transformation_matrix", &CalibrationService::calculate_transformation_matrix)
        .def("matrix_to_json", &CalibrationService::matrix_to_json)
        .def("json_to_matrix", &CalibrationService::json_to_matrix);
    
    // HeadPoseEstimator
    py::class_<HeadPoseEstimator>(m, "HeadPoseEstimator")
        .def(py::init<>())
        .def("estimate", &HeadPoseEstimator::estimate);
    
    // GazeEstimator
    py::class_<GazeEstimator>(m, "GazeEstimator")
        .def(py::init<int>(), py::arg("smoothing_window") = 5)
        .def("estimate", &GazeEstimator::estimate)
        .def("reset_smoothing", &GazeEstimator::reset_smoothing);
    
    // KPICalculator
    py::class_<KPICalculator>(m, "KPICalculator")
        .def(py::init<>())
        .def("calculate_productivity_metrics", &KPICalculator::calculate_productivity_metrics);
    
    // StressAnalyzer
    py::class_<StressAnalyzer>(m, "StressAnalyzer")
        .def(py::init<int>(), py::arg("sample_rate") = 16000)
        .def("analyze", &StressAnalyzer::analyze);
    
    // EncryptionManager
    py::class_<EncryptionManager>(m, "EncryptionManager")
        .def(py::init<std::string>(), py::arg("master_key") = "")
        .def("encrypt", &EncryptionManager::encrypt)
        .def("decrypt", &EncryptionManager::decrypt);
}

#endif // EAGLEARN_ML_H
