import SwiftUI

struct ObjectDetailsView: View {
    let objects: [ScannedObject]

    @StateObject private var audioService = GuidanceAudioService()

    private let accentGradient = LinearGradient(
        colors: [
            Color(red: 0.12, green: 0.86, blue: 0.70),
            Color(red: 0.08, green: 0.75, blue: 0.80),
            Color(red: 0.18, green: 0.55, blue: 0.98)
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    init(objects: [ScannedObject] = []) {
        self.objects = objects
    }

    var body: some View {
        VStack(spacing: 18) {
            askQuestionButton

            if objects.isEmpty {
                emptyState
            } else {
                objectHistory
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, 18)
        .background(Color.white.ignoresSafeArea())
        .navigationTitle("Scanned Objects")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            audioService.speak(spokenIntroduction, respectsVoiceSetting: false)
        }
        .onDisappear {
            audioService.stop()
        }
    }

    private var askQuestionButton: some View {
        Button {
            audioService.stop()
        } label: {
            HStack(spacing: 12) {
                Image(systemName: "questionmark.bubble.fill")
                Text("Ask a question")
            }
            .font(.system(size: 20, weight: .heavy, design: .rounded))
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity, minHeight: 76)
            .background(accentGradient, in: RoundedRectangle(cornerRadius: 24, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .stroke(.white.opacity(0.65), lineWidth: 2)
            )
            .shadow(
                color: Color(red: 0.08, green: 0.72, blue: 0.76).opacity(0.28),
                radius: 14,
                x: 0,
                y: 8
            )
        }
        .buttonStyle(.plain)
        .accessibilityHint("Ask about products you have scanned")
    }

    private var emptyState: some View {
        VStack(spacing: 18) {
            Spacer()

            Image(systemName: "shippingbox")
                .font(.system(size: 64, weight: .medium))
                .foregroundStyle(accentGradient)

            Text("No scanned objects yet")
                .font(.title2.weight(.bold))

            Text("Objects you scan will appear here when history becomes available.")
                .font(.body.weight(.medium))
                .foregroundStyle(.gray)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .accessibilityElement(children: .combine)
    }

    private var objectHistory: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 22) {
                ForEach(objects.groupedByDay) { section in
                    VStack(alignment: .leading, spacing: 10) {
                        Text(Self.displayDate(section.date))
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.gray)
                            .accessibilityAddTraits(.isHeader)

                        ForEach(section.objects) { object in
                            objectRow(object)
                        }
                    }
                }
            }
            .padding(.vertical, 4)
        }
    }

    private func objectRow(_ object: ScannedObject) -> some View {
        HStack(spacing: 14) {
            AsyncImage(url: object.thumbnailURL) { image in
                image.resizable().scaledToFill()
            } placeholder: {
                ZStack {
                    Color.black.opacity(0.06)
                    Image(systemName: "photo")
                        .foregroundStyle(.gray)
                }
            }
            .frame(width: 68, height: 68)
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))

            VStack(alignment: .leading, spacing: 5) {
                Text(object.name.capitalized)
                    .font(.headline.weight(.bold))
                    .foregroundStyle(.black)

                Text(object.details?.isEmpty == false ? object.details! : "Details not available yet…")
                    .font(.subheadline)
                    .foregroundStyle(.gray)
                    .lineLimit(2)
                    .truncationMode(.tail)
            }

            Spacer(minLength: 4)
            Image(systemName: "chevron.right")
                .font(.subheadline.weight(.bold))
                .foregroundStyle(.gray)
        }
        .padding(12)
        .background(.white, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke(.black.opacity(0.08), lineWidth: 1)
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(object.name). \(object.details ?? "Details not available yet")")
    }

    private var spokenIntroduction: String {
        let instruction = "Tap the top of the screen to ask any question about the products you scanned."
        guard !objects.isEmpty else {
            return instruction + " You have no scanned objects yet."
        }

        let summaries = objects.groupedByDay.map { section in
            let names = section.objects.map(\.name).joined(separator: ", ")
            return "On \(Self.spokenDate(section.date)), you scanned: \(names)."
        }
        return ([instruction] + summaries).joined(separator: " ")
    }

    private static func displayDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US")
        formatter.dateFormat = "EEEE"
        let weekday = formatter.string(from: date)
        formatter.dateFormat = "MMMM yyyy"
        let monthAndYear = formatter.string(from: date)
        let day = Calendar.current.component(.day, from: date)
        return "\(weekday) \(ordinal(day)), \(monthAndYear)"
    }

    private static func spokenDate(_ date: Date) -> String {
        displayDate(date)
    }

    private static func ordinal(_ number: Int) -> String {
        let remainder100 = number % 100
        if 11...13 ~= remainder100 { return "\(number)th" }
        switch number % 10 {
        case 1: return "\(number)st"
        case 2: return "\(number)nd"
        case 3: return "\(number)rd"
        default: return "\(number)th"
        }
    }
}

#Preview {
    NavigationStack {
        ObjectDetailsView()
    }
}
