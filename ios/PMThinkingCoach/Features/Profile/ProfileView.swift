import SwiftUI

/// Profile (spec §10.12). Goal, language, privacy, sign out, account deletion.
/// No paywall and no upgrade call to action in the MVP (spec §20, §24).
struct ProfileView: View {
    @EnvironmentObject private var session: SessionStore
    @EnvironmentObject private var container: AppContainer
    @EnvironmentObject private var language: LanguageStore
    @StateObject private var viewModel: ProfileViewModel
    @State private var showingPrivacy = false
    @State private var showingDeleteConfirmation = false
    @State private var showingSignOutConfirmation = false

    init(viewModel: @autoclosure @escaping () -> ProfileViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel())
    }

    var body: some View {
        NavigationStack {
            Form {
                if let me = session.me {
                    Section(S.Profile.practiceSection) {
                        LabeledContent(S.Profile.level, value: "\(me.level)")
                        LabeledContent(S.Profile.totalXp, value: "\(me.totalXp)")
                        LabeledContent(
                            S.Profile.targetRole,
                            value: S.Roles.title(me.targetRole)
                        )
                    }
                }

                Section {
                    // Глоссарий доступен и из урока, и отсюда: для новичка это
                    // условие читаемости домена, а не украшение.
                    NavigationLink {
                        GlossaryView(
                            viewModel: GlossaryViewModel(
                                client: container.apiClient,
                                analytics: container.analytics,
                                source: "profile"
                            )
                        )
                    } label: {
                        Label(S.Glossary.title, systemImage: "character.book.closed")
                    }
                }

                Section {
                    Picker(S.Profile.targetRole, selection: roleBinding) {
                        Text(S.Roles.none).tag("")
                        ForEach(S.Roles.keys, id: \.self) { key in
                            Text(S.Roles.title(key)).tag(key)
                        }
                    }
                } header: {
                    Text(S.Profile.roleSection)
                } footer: {
                    Text(S.Profile.roleFooter)
                }

                Section {
                    Picker(S.Profile.languageLabel, selection: languageBinding) {
                        ForEach(AppLanguage.allCases) { option in
                            Text(option.displayName).tag(option)
                        }
                    }
                    .pickerStyle(.segmented)
                } header: {
                    Text(S.Profile.languageSection)
                } footer: {
                    Text(S.Profile.languageFooter)
                }

                Section(S.Profile.privacySection) {
                    Button {
                        showingPrivacy = true
                    } label: {
                        Label(S.Profile.privacyNotice, systemImage: "hand.raised")
                    }
                    .frame(minHeight: Theme.minimumTapTarget)
                }

                if AppConfig.allowsDeveloperSignIn {
                    Section {
                        TextField("http://localhost:8000", text: $viewModel.baseURLOverride)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .keyboardType(.URL)
                        Button(S.Profile.apply) { viewModel.applyBaseURLOverride() }
                            .frame(minHeight: Theme.minimumTapTarget)
                    } header: {
                        Text(S.Profile.developerSection)
                    } footer: {
                        Text(S.Profile.developerFooter)
                    }
                }

                Section {
                    Button(role: .destructive) {
                        showingSignOutConfirmation = true
                    } label: {
                        Label(S.Profile.signOut, systemImage: "rectangle.portrait.and.arrow.right")
                    }
                    .frame(minHeight: Theme.minimumTapTarget)

                    Button(role: .destructive) {
                        showingDeleteConfirmation = true
                    } label: {
                        Label(S.Profile.deleteAccount, systemImage: "trash")
                    }
                    .frame(minHeight: Theme.minimumTapTarget)
                } footer: {
                    Text(S.Profile.deleteFooter)
                }

                if let error = viewModel.error {
                    Section {
                        Text(error.userMessage)
                            .font(.footnote)
                            .foregroundStyle(Theme.Palette.negative)
                    }
                }

                Section {
                    Text(S.Profile.version(AppConfig.appVersion, AppConfig.buildNumber))
                        .font(.footnote)
                        .foregroundStyle(Theme.Palette.tertiaryText)
                }
            }
            // Форма — единственный экран на системном фоне; на песочной палитре
            // он читался бы холодным серым посреди тёплого приложения.
            .scrollContentBackground(.hidden)
            .background(Theme.Palette.background)
            .animation(Motion.standard, value: viewModel.error)
            .navigationTitle(S.Profile.title)
            .sheet(isPresented: $showingPrivacy) { PrivacyNoticeView() }
            .confirmationDialog(
                S.Profile.signOutQuestion,
                isPresented: $showingSignOutConfirmation,
                titleVisibility: .visible
            ) {
                Button(S.Profile.signOut, role: .destructive) {
                    Task { await viewModel.signOut() }
                }
                Button(S.Common.cancel, role: .cancel) {}
            } message: {
                Text(S.Profile.signOutMessage)
            }
            .confirmationDialog(
                S.Profile.deleteQuestion,
                isPresented: $showingDeleteConfirmation,
                titleVisibility: .visible
            ) {
                Button(S.Profile.deletePermanently, role: .destructive) {
                    Task { await viewModel.deleteAccount() }
                }
                Button(S.Common.cancel, role: .cancel) {}
            } message: {
                Text(S.Profile.deleteMessage)
            }
            .overlay {
                if viewModel.isDeleting {
                    LoadingState(message: S.Profile.deleting)
                        .background(.ultraThinMaterial)
                        .transition(.opacity)
                }
            }
        }
    }

    private var roleBinding: Binding<String> {
        Binding(
            get: { session.me?.targetRole ?? "" },
            set: { newValue in Task { await viewModel.changeRole(newValue) } }
        )
    }

    /// Applies immediately — the whole view tree is keyed on the language at the app
    /// root, and the next request already asks the server for content in the new one.
    private var languageBinding: Binding<AppLanguage> {
        Binding(
            get: { language.language },
            set: { newValue in
                Haptics.selection()
                container.setLanguage(newValue)
            }
        )
    }
}
