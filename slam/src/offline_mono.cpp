#include <System.h>

#include <opencv2/videoio.hpp>

#include <chrono>
#include <filesystem>
#include <iostream>
#include <string>

namespace {

constexpr int kTrackingOk = 2;

}  // namespace

int main(int argc, char** argv) {
    if (argc != 5) {
        std::cerr << "Usage: offline_mono vocabulary settings video points.txt\n";
        return 1;
    }

    const std::string vocabulary = argv[1];
    const std::string settings = argv[2];
    const std::string video_path = argv[3];
    const std::string points_path = argv[4];

    cv::VideoCapture capture(video_path);
    if (!capture.isOpened()) {
        std::cerr << "cannot open " << video_path << "\n";
        return 1;
    }

    double fps = capture.get(cv::CAP_PROP_FPS);
    if (fps < 1.0) {
        fps = 30.0;
    }
    std::cout << "fps " << fps << "\n" << std::flush;

    ORB_SLAM3::System slam(vocabulary, settings, ORB_SLAM3::System::MONOCULAR, false);

    cv::Mat frame;
    int frame_index = 0;
    int tracked = 0;
    const auto started = std::chrono::steady_clock::now();
    while (capture.read(frame)) {
        const double timestamp = static_cast<double>(frame_index) / fps;
        slam.TrackMonocular(frame, timestamp);
        if (slam.GetTrackingState() == kTrackingOk) {
            tracked += 1;
        }
        if (frame_index % 30 == 0) {
            std::cout << "frame " << frame_index << " state " << slam.GetTrackingState() << "\n" << std::flush;
        }
        frame_index += 1;
    }

    slam.Shutdown();
    const std::filesystem::path points_file(points_path);
    std::filesystem::create_directories(points_file.parent_path());
    slam.SaveTimedMapPoints(points_path);
    const std::filesystem::path poses_file =
        points_file.parent_path() / (points_file.stem().string() + "_poses.txt");
    slam.SaveCameraPoses(poses_file.string());

    const auto elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
    std::cout << "frames " << frame_index << " tracked_ok " << tracked << " seconds " << elapsed << "\n";
    return frame_index > 0 ? 0 : 1;
}
