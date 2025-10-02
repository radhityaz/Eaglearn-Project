#!/usr/bin/env python3
"""
PROTOTYPE TYPE: THROWAWAY -> EVOLUTIONARY (if performance meets targets)
PURPOSE: Optimized webcam capture using MSMF backend
EVIDENCE TARGET: CPU <15%, RAM <300MB, Latency <100ms, FPS >15

Changes from previous version:
1. Using CAP_MSMF instead of CAP_DSHOW
2. Added threading for non-blocking capture
3. Implemented frame buffer
4. Optimized CPU measurement
"""

import cv2
import numpy as np
import time
import psutil
import os
import sys
import threading
import queue
from collections import deque
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    fps: float = 0.0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    frame_latency_ms: float = 0.0
    dropped_frames: int = 0
    resolution: Tuple[int, int] = (1280, 720)


class ThreadedCamera:
    """Threaded camera capture for non-blocking operation"""
    
    def __init__(self, device_id: int = 0, buffer_size: int = 2):
        self.device_id = device_id
        self.cap = None
        self.frame_queue = queue.Queue(maxsize=buffer_size)
        self.capture_thread = None
        self.running = False
        self.frame_count = 0
        self.dropped_count = 0
        
    def start(self, resolution=(1280, 720), fps=30):
        """Start camera capture in separate thread"""
        print(f"🎥 Initializing camera with MSMF backend...")
        
        # Use MSMF backend for Windows (usually faster than DirectShow)
        self.cap = cv2.VideoCapture(self.device_id, cv2.CAP_MSMF)
        
        if not self.cap.isOpened():
            print("❌ Failed with MSMF, trying default backend...")
            self.cap = cv2.VideoCapture(self.device_id)
            
        if not self.cap.isOpened():
            print("❌ ERROR: Could not open webcam")
            return False
        
        # Configure camera
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer
        
        # Set backend-specific optimizations
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        
        # Get actual settings
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        backend = self.cap.getBackendName()
        
        print(f"✅ Camera ready: {actual_width}x{actual_height} @ {actual_fps:.1f} FPS")
        print(f"   Backend: {backend}")
        
        # Start capture thread
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        
        return True
    
    def _capture_loop(self):
        """Continuous capture in separate thread"""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame_count += 1
                
                # Try to put frame in queue (non-blocking)
                try:
                    # Remove old frame if queue is full
                    if self.frame_queue.full():
                        try:
                            self.frame_queue.get_nowait()
                            self.dropped_count += 1
                        except queue.Empty:
                            pass
                    
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    self.dropped_count += 1
            
            # Small sleep to prevent CPU spinning
            time.sleep(0.001)
    
    def get_frame(self, timeout=0.1):
        """Get latest frame from buffer"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def stop(self):
        """Stop capture and release resources"""
        self.running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()


class OptimizedWebcamBenchmark:
    """Optimized benchmark with threaded capture"""
    
    def __init__(self):
        self.camera = ThreadedCamera(device_id=0, buffer_size=2)
        self.metrics = PerformanceMetrics()
        self.process = psutil.Process(os.getpid())
        
        # Performance tracking
        self.cpu_samples = []
        self.memory_samples = []
        self.latency_samples = []
        self.fps_history = deque(maxlen=30)
        
    def run_test(self, duration_seconds: int = 30):
        """Run optimized performance test"""
        print("="*60)
        print("EAGLEARN OPTIMIZED WEBCAM TEST (MSMF Backend)")
        print("="*60)
        print(f"\n📊 Starting {duration_seconds}-second benchmark...")
        print("⚡ Using threaded capture with MSMF backend\n")
        
        # Start camera
        if not self.camera.start(resolution=(1280, 720), fps=30):
            return
        
        # Wait for camera to stabilize
        print("⏳ Warming up camera (2 seconds)...")
        time.sleep(2)
        
        # Clear any buffered frames
        while self.camera.get_frame(timeout=0.01) is not None:
            pass
        
        print("\n📈 Live Metrics:")
        print("-" * 50)
        
        start_time = time.time()
        last_report = start_time
        frame_count = 0
        
        try:
            while (time.time() - start_time) < duration_seconds:
                loop_start = time.perf_counter()
                
                # Get frame from buffer
                frame = self.camera.get_frame(timeout=0.033)  # ~30 FPS timeout
                
                if frame is not None:
                    frame_count += 1
                    
                    # Simulate processing (lightweight)
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    small = cv2.resize(gray, (160, 120))
                    
                    # Calculate frame latency
                    latency_ms = (time.perf_counter() - loop_start) * 1000
                    self.latency_samples.append(latency_ms)
                
                # Update metrics periodically
                current_time = time.time()
                elapsed = current_time - start_time
                
                if current_time - last_report >= 2.0:
                    # Get resource metrics
                    cpu = self.process.cpu_percent(interval=0.1)
                    mem = self.process.memory_info().rss / 1024 / 1024
                    
                    self.cpu_samples.append(cpu)
                    self.memory_samples.append(mem)
                    
                    # Calculate FPS
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    self.fps_history.append(fps)
                    
                    # Calculate average latency
                    avg_latency = np.mean(self.latency_samples[-100:]) if self.latency_samples else 0
                    
                    # Print live stats
                    print(f"  [{int(elapsed):02d}s] "
                          f"FPS: {fps:5.1f} | "
                          f"CPU: {cpu:5.1f}% | "
                          f"RAM: {mem:6.1f}MB | "
                          f"Latency: {avg_latency:5.1f}ms")
                    
                    last_report = current_time
                
                # Prevent CPU spinning
                remaining = 0.033 - (time.perf_counter() - loop_start)
                if remaining > 0:
                    time.sleep(remaining)
                    
        except KeyboardInterrupt:
            print("\n⚠ Test interrupted")
        finally:
            self.camera.stop()
            self._print_results(frame_count, time.time() - start_time)
    
    def _print_results(self, total_frames: int, duration: float):
        """Print final test results"""
        print("\n" + "="*60)
        print("📊 OPTIMIZED BENCHMARK RESULTS")
        print("="*60)
        
        # Calculate final metrics
        if self.cpu_samples:
            cpu_avg = np.mean(self.cpu_samples)
            cpu_max = np.max(self.cpu_samples)
            cpu_pass = cpu_avg < 15
            
            print(f"\n🖥️ CPU Usage:")
            print(f"  Average: {cpu_avg:.1f}%")
            print(f"  Peak:    {cpu_max:.1f}%")
            print(f"  Target:  <15%")
            print(f"  Status:  {'✅ PASS' if cpu_pass else '❌ FAIL'}")
        
        if self.memory_samples:
            mem_avg = np.mean(self.memory_samples)
            mem_max = np.max(self.memory_samples)
            mem_pass = mem_max < 300
            
            print(f"\n💾 Memory Usage:")
            print(f"  Average: {mem_avg:.1f} MB")
            print(f"  Peak:    {mem_max:.1f} MB")
            print(f"  Target:  <300 MB")
            print(f"  Status:  {'✅ PASS' if mem_pass else '❌ FAIL'}")
        
        if self.latency_samples:
            lat_avg = np.mean(self.latency_samples)
            lat_p95 = np.percentile(self.latency_samples, 95)
            lat_pass = lat_p95 < 100
            
            print(f"\n⏱️ Frame Latency:")
            print(f"  Average: {lat_avg:.1f} ms")
            print(f"  P95:     {lat_p95:.1f} ms")
            print(f"  Target:  <100 ms")
            print(f"  Status:  {'✅ PASS' if lat_pass else '❌ FAIL'}")
        
        # FPS calculation
        actual_fps = total_frames / duration if duration > 0 else 0
        fps_pass = actual_fps > 15
        
        print(f"\n📹 Frame Statistics:")
        print(f"  Total frames:   {total_frames}")
        print(f"  Capture frames: {self.camera.frame_count}")
        print(f"  Dropped frames: {self.camera.dropped_count}")
        print(f"  Processed FPS:  {actual_fps:.1f}")
        print(f"  Target FPS:     >15")
        print(f"  Status:         {'✅ PASS' if fps_pass else '❌ FAIL'}")
        
        print("\n" + "="*60)
        
        # Overall assessment
        all_pass = (
            (not self.cpu_samples or cpu_pass) and
            (not self.memory_samples or mem_pass) and
            (not self.latency_samples or lat_pass) and
            fps_pass
        )
        
        print("\n📋 FINAL ASSESSMENT:")
        if all_pass:
            print("✅ ALL TARGETS MET WITH OPTIMIZATION!")
            print("   Ready to promote to EVOLUTIONARY prototype")
            print("   Proceed with gaze estimation implementation")
        else:
            print("⚠️ SOME TARGETS STILL NOT MET")
            
            # Provide specific recommendations
            if not fps_pass:
                print("\n   FPS Issue:")
                print("   - Try reducing resolution to 640x480")
                print("   - Or adjust FPS target to 10 via Change Request")
            
            if self.latency_samples and not lat_pass:
                print("\n   Latency Issue:")
                print("   - Consider frame skipping (process every 2nd frame)")
                print("   - Or adjust latency target to 150ms via Change Request")
        
        print("\n" + "="*60)
        
        # Save evidence
        print("\n📝 EVIDENCE SUMMARY:")
        print(f"- Backend used: MSMF (optimized)")
        print(f"- Threading: Enabled")
        print(f"- Buffer size: 2 frames")
        print(f"- Performance gain: Check vs previous test")
        
        return all_pass


def main():
    """Run the optimized benchmark"""
    benchmark = OptimizedWebcamBenchmark()
    success = benchmark.run_test(duration_seconds=30)
    
    if success:
        print("\n🎯 NEXT STEPS:")
        print("1. Promote to EVOLUTIONARY prototype")
        print("2. Integrate with main backend")
        print("3. Add gaze estimation module")
    else:
        print("\n🔧 OPTIMIZATION OPTIONS:")
        print("1. Try 640x480 resolution")
        print("2. Process every 2nd frame")
        print("3. Submit CR for adjusted targets")


if __name__ == "__main__":
    main()