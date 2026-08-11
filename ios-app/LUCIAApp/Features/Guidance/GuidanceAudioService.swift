import AVFoundation
import Combine
import Foundation

@MainActor
final class GuidanceAudioService: NSObject, ObservableObject, AVSpeechSynthesizerDelegate {
    private let synthesizer = AVSpeechSynthesizer()
    private var lastMessage: String?
    private var lastSpokenAt = Date.distantPast
    private let minimumRepeatInterval: TimeInterval = 5

    override init() {
        super.init()
        synthesizer.delegate = self
    }

    func speak(_ message: String, respectsVoiceSetting: Bool = true) {
        guard !respectsVoiceSetting || AppSettingsStore.voiceGuidanceEnabled else {
            stop()
            return
        }

        let now = Date()
        guard !synthesizer.isSpeaking else { return }
        guard message != lastMessage || now.timeIntervalSince(lastSpokenAt) >= minimumRepeatInterval else { return }

        let utterance = AVSpeechUtterance(string: message)
        utterance.rate = AppSettingsStore.speechRate
        utterance.volume = 1
        synthesizer.speak(utterance)
        lastMessage = message
        lastSpokenAt = now
    }

    func stop() {
        synthesizer.stopSpeaking(at: .immediate)
        lastMessage = nil
        lastSpokenAt = .distantPast
    }
}
