import SwiftUI

/// Profile (spec §10.12). Goal, privacy, sign out, account deletion.
/// No paywall and no upgrade call to action in the MVP (spec §20, §24).
struct ProfileView: View {
    @EnvironmentObject private var session: SessionStore
    @StateObject private var viewModel: ProfileViewModel
    @State private var showingPrivacy = false
    @State private var showingDeleteConfirmation = false
    @State private var showingSignOutConfirmation = false

    private let goals: [(id: String, title: String)] = [
        ("break_into_pm", "Break into PM"),
        ("grow_in_first_role", "Grow in my first PM role"),
        ("practise_product_thinking", "Practise product thinking")
    ]

    init(viewModel: @autoclosure @escaping () -> ProfileViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel())
    }

    var body: some View {
        NavigationStack {
            Form {
                if let me = session.me {
                    Section("Your practice") {
                        LabeledContent("Level", value: "\(me.level)")
                        LabeledContent("Total XP", value: "\(me.totalXp)")
                        LabeledContent(
                            "Starting level",
                            value: Theme.levelLabel(me.startingLevel ?? "foundation")
                        )
                    }
                }

                Section {
                    Picker("Goal", selection: goalBinding) {
                        ForEach(goals, id: \.id) { goal in
                            Text(goal.title).tag(goal.id)
                        }
                    }
                } header: {
                    Text("Goal")
                } footer: {
                    Text("Changing your goal affects future challenges only. Your past results and skill scores stay as they are.")
                }

                Section("Privacy") {
                    Button {
                        showingPrivacy = true
                    } label: {
                        Label("Privacy notice", systemImage: "hand.raised")
                    }
                    .frame(minHeight: Theme.minimumTapTarget)
                }

                if AppConfig.allowsDeveloperSignIn {
                    Section {
                        TextField("http://localhost:8000", text: $viewModel.baseURLOverride)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .keyboardType(.URL)
                        Button("Apply") { viewModel.applyBaseURLOverride() }
                            .frame(minHeight: Theme.minimumTapTarget)
                    } header: {
                        Text("Developer")
                    } footer: {
                        Text("Point the app at a different API host. Debug builds only. Restart the app after changing this.")
                    }
                }

                Section {
                    Button(role: .destructive) {
                        showingSignOutConfirmation = true
                    } label: {
                        Label("Sign out", systemImage: "rectangle.portrait.and.arrow.right")
                    }
                    .frame(minHeight: Theme.minimumTapTarget)

                    Button(role: .destructive) {
                        showingDeleteConfirmation = true
                    } label: {
                        Label("Delete account", systemImage: "trash")
                    }
                    .frame(minHeight: Theme.minimumTapTarget)
                } footer: {
                    Text("Deleting your account removes your written responses, your feedback, and your identity link. This cannot be undone.")
                }

                if let error = viewModel.error {
                    Section {
                        Text(error.userMessage)
                            .font(.footnote)
                            .foregroundStyle(Theme.Palette.negative)
                    }
                }

                Section {
                    Text("Version \(AppConfig.appVersion) (\(AppConfig.buildNumber))")
                        .font(.footnote)
                        .foregroundStyle(Theme.Palette.tertiaryText)
                }
            }
            .navigationTitle("Profile")
            .sheet(isPresented: $showingPrivacy) { PrivacyNoticeView() }
            .confirmationDialog(
                "Sign out?", isPresented: $showingSignOutConfirmation, titleVisibility: .visible
            ) {
                Button("Sign out", role: .destructive) {
                    Task { await viewModel.signOut() }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("Any draft that hasn't synced yet will be cleared from this device.")
            }
            .confirmationDialog(
                "Delete your account?",
                isPresented: $showingDeleteConfirmation,
                titleVisibility: .visible
            ) {
                Button("Delete permanently", role: .destructive) {
                    Task { await viewModel.deleteAccount() }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This removes your responses, feedback and identity link. It cannot be undone.")
            }
            .overlay {
                if viewModel.isDeleting {
                    LoadingState(message: "Deleting your account…")
                        .background(.ultraThinMaterial)
                }
            }
        }
    }

    private var goalBinding: Binding<String> {
        Binding(
            get: { session.me?.goal ?? "break_into_pm" },
            set: { newValue in Task { await viewModel.changeGoal(newValue) } }
        )
    }
}
