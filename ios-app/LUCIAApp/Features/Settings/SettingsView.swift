import SwiftUI

struct SettingsView: View {
    @AppStorage(AppSettingsStore.Key.apiBaseURL)
    private var apiBaseURL = AppSettingsStore.defaultAPIBaseURLString

    @AppStorage(AppSettingsStore.Key.voiceGuidanceEnabled)
    private var voiceGuidanceEnabled = true

    @AppStorage(AppSettingsStore.Key.speechRate)
    private var speechRate = 0.48

    @AppStorage(AppSettingsStore.Key.hapticsEnabled)
    private var hapticsEnabled = true

    @AppStorage(AppSettingsStore.Key.guidanceInterval)
    private var guidanceInterval = 2.0

    private var isServerURLValid: Bool {
        AppSettingsStore.normalizedURL(from: apiBaseURL) != nil
    }

    var body: some View {
        Form {
            Section {
                TextField("http://192.168.1.20:8000", text: $apiBaseURL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.URL)
                    .accessibilityLabel("Detection server address")

                if !isServerURLValid {
                    Label("Enter a complete HTTP or HTTPS address.", systemImage: "exclamationmark.triangle.fill")
                        .font(.footnote.weight(.semibold))
                }
            } header: {
                Text("Detection Server")
            } footer: {
                Text("For an iPhone, use the address of the Mac running LUCIA, including port 8000.")
            }

            Section("Voice Guidance") {
                Toggle("Speak camera instructions", isOn: $voiceGuidanceEnabled)

                VStack(alignment: .leading, spacing: 8) {
                    Text("Speech speed")
                    Slider(value: $speechRate, in: 0.35...0.60, step: 0.01) {
                        Text("Speech speed")
                    } minimumValueLabel: {
                        Image(systemName: "tortoise.fill")
                    } maximumValueLabel: {
                        Image(systemName: "hare.fill")
                    }
                }
                .disabled(!voiceGuidanceEnabled)
            }

            Section("Camera Feedback") {
                Toggle("Capture haptics", isOn: $hapticsEnabled)

                Stepper(value: $guidanceInterval, in: 1.0...5.0, step: 0.5) {
                    LabeledContent("Guidance frequency") {
                        Text("\(guidanceInterval, specifier: "%.1f") seconds")
                    }
                }
            }

            Section {
                Button("Restore Defaults") {
                    apiBaseURL = AppSettingsStore.defaultAPIBaseURLString
                    voiceGuidanceEnabled = true
                    speechRate = 0.48
                    hapticsEnabled = true
                    guidanceInterval = 2.0
                }
                .foregroundStyle(.black)
            }
        }
        .tint(.black)
        .preferredColorScheme(.light)
        .navigationTitle("Settings")
        .navigationBarTitleDisplayMode(.inline)
    }
}
