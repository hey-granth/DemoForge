import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from worker.recorder import VideoProcessor


@pytest.fixture
def temp_videos(tmp_path):
    input_video = tmp_path / "input.webm"
    input_video.write_bytes(b"fake_video_data")

    output_video = tmp_path / "output.mp4"

    return input_video, output_video


class TestVideoProcessor:
    def test_initialization(self):
        processor = VideoProcessor(target_fps=30)
        assert processor.target_fps == 30

    @patch("worker.recorder.subprocess.run")
    def test_process_video_success(self, mock_run, temp_videos):
        input_video, output_video = temp_videos

        mock_run.return_value = MagicMock(returncode=0)

        with patch.object(Path, "exists", return_value=True):
            processor = VideoProcessor()

            with patch.object(processor, "_get_video_duration", return_value=10.0):
                processor.process_video(input_video, output_video)

                assert mock_run.called
                assert "ffmpeg" in mock_run.call_args[0][0]

    def test_process_video_input_not_found(self, tmp_path):
        processor = VideoProcessor()
        input_video = tmp_path / "nonexistent.webm"
        output_video = tmp_path / "output.mp4"

        with pytest.raises(FileNotFoundError):
            processor.process_video(input_video, output_video)

    @patch("worker.recorder.subprocess.run")
    def test_process_video_ffmpeg_failure(self, mock_run, temp_videos):
        input_video, output_video = temp_videos

        from subprocess import CalledProcessError

        mock_run.side_effect = CalledProcessError(1, "ffmpeg", stderr=b"Error")

        processor = VideoProcessor()

        with pytest.raises(RuntimeError, match="FFmpeg processing failed"):
            with patch.object(processor, "_get_video_duration", return_value=10.0):
                processor.process_video(input_video, output_video)

    @patch("worker.recorder.subprocess.run")
    def test_process_video_timeout(self, mock_run, temp_videos):
        input_video, output_video = temp_videos

        from subprocess import TimeoutExpired

        mock_run.side_effect = TimeoutExpired("ffmpeg", 120)

        processor = VideoProcessor()

        with pytest.raises(RuntimeError, match="timed out"):
            with patch.object(processor, "_get_video_duration", return_value=10.0):
                processor.process_video(input_video, output_video)

    @patch("worker.recorder.subprocess.run")
    def test_process_video_trims_idle_time(self, mock_run, temp_videos):
        input_video, output_video = temp_videos

        mock_run.return_value = MagicMock(returncode=0)

        processor = VideoProcessor()

        with patch.object(Path, "exists", return_value=True):
            with patch.object(processor, "_get_video_duration", return_value=10.0):
                processor.process_video(
                    input_video, output_video, trim_start=0.5, trim_end=0.5
                )

                args = mock_run.call_args[0][0]
                assert "-ss" in args
                assert "-to" in args

    @patch("worker.recorder.subprocess.run")
    def test_get_video_duration(self, mock_run):
        mock_run.return_value = MagicMock(stdout=b"45.5", returncode=0)

        processor = VideoProcessor()
        duration = processor._get_video_duration(Path("/fake/video.mp4"))

        assert duration == 45.5
        assert "ffprobe" in mock_run.call_args[0][0]

    @patch("worker.recorder.subprocess.run")
    def test_get_video_duration_failure(self, mock_run):
        from subprocess import CalledProcessError

        mock_run.side_effect = CalledProcessError(1, "ffprobe")

        processor = VideoProcessor()
        duration = processor._get_video_duration(Path("/fake/video.mp4"))

        assert duration == 0.0

    def test_cleanup_removes_files(self, tmp_path):
        file1 = tmp_path / "temp1.webm"
        file2 = tmp_path / "temp2.mp4"
        file1.write_bytes(b"data")
        file2.write_bytes(b"data")

        processor = VideoProcessor()
        processor.cleanup(file1, file2)

        assert not file1.exists()
        assert not file2.exists()

    def test_cleanup_handles_nonexistent_files(self, tmp_path):
        processor = VideoProcessor()
        processor.cleanup(tmp_path / "nonexistent.mp4")

    @patch("worker.recorder.subprocess.run")
    def test_skips_trim_for_short_videos(self, mock_run, temp_videos):
        input_video, output_video = temp_videos

        mock_run.return_value = MagicMock(returncode=0)

        processor = VideoProcessor()

        with patch.object(Path, "exists", return_value=True):
            with patch.object(processor, "_get_video_duration", return_value=0.5):
                processor.process_video(input_video, output_video)

                args = mock_run.call_args[0][0]
                ss_index = args.index("-ss") if "-ss" in args else -1
                if ss_index != -1:
                    assert args[ss_index + 1] == "0"
