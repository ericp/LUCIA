import AVFoundation
import CoreImage
import Foundation
import ImageIO

final class FrameCapture: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    private let lock = NSLock()
    private let context = CIContext(options: [.cacheIntermediates: false])
    private var latestJPEG: Data?
    private var lastProcessedAt = Date.distantPast

    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        let now = Date()
        guard now.timeIntervalSince(lastProcessedAt) >= 0.75 else { return }
        lastProcessedAt = now

        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }

        let orientedImage = CIImage(cvPixelBuffer: pixelBuffer)
            .oriented(.right)
        let longestSide = max(orientedImage.extent.width, orientedImage.extent.height)
        let scale = min(1, 640 / longestSide)
        let image = orientedImage.transformed(by: CGAffineTransform(scaleX: scale, y: scale))
        let colorSpace = CGColorSpaceCreateDeviceRGB()
        guard let data = context.jpegRepresentation(
            of: image,
            colorSpace: colorSpace,
            options: [:]
        ) else { return }

        lock.lock()
        latestJPEG = data
        lock.unlock()
    }

    func latestFrameData() -> Data? {
        lock.lock()
        defer { lock.unlock() }
        return latestJPEG
    }
}
