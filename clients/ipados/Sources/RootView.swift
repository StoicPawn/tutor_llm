import SwiftUI

struct RootView: View {
    @EnvironmentObject var state: AppState
    @State private var showSettings = false

    var body: some View {
        Group {
            if state.isConfigured {
                NavigationSplitView {
                    List(selection: Binding(
                        get: { state.selectedWorkspace },
                        set: { newValue in if let newValue { Task { await state.select(workspace: newValue) } } }
                    )) {
                        Section("Workspace") {
                            ForEach(state.workspaces) { workspace in
                                Text(workspace.name).tag(workspace as Workspace?)
                            }
                        }
                        if !state.documents.isEmpty {
                            Section("Documenti") {
                                ForEach(state.documents) { document in
                                    Button {
                                        state.selectedDocument = document
                                    } label: {
                                        Label(document.name, systemImage: state.selectedDocument?.id == document.id ? "doc.fill" : "doc")
                                    }
                                }
                            }
                        }
                    }
                    .navigationTitle("Tutor LLM")
                    .toolbar {
                        ToolbarItem(placement: .topBarTrailing) {
                            Button { showSettings = true } label: { Image(systemName: "gear") }
                        }
                    }
                } detail: {
                    StudioView()
                }
                .task { await state.reloadWorkspaces() }
            } else {
                ConnectionView()
            }
        }
        .sheet(isPresented: $showSettings) { ConnectionView(isSheet: true) }
        .alert("Tutor LLM", isPresented: Binding(
            get: { state.errorMessage != nil },
            set: { if !$0 { state.errorMessage = nil } }
        )) { Button("OK", role: .cancel) {} } message: { Text(state.errorMessage ?? "") }
    }
}

struct ConnectionView: View {
    @EnvironmentObject var state: AppState
    var isSheet = false
    @Environment(\.dismiss) private var dismiss
    @State private var url = ""
    @State private var token = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Tutor Server") {
                    TextField("https://tutor.example oppure http://server:8000", text: $url)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                    SecureField("Token dispositivo", text: $token)
                }
                Section {
                    Button("Connetti") {
                        Task {
                            await state.configure(serverURL: url, token: token)
                            if state.isConfigured && isSheet { dismiss() }
                        }
                    }
                    .disabled(url.isEmpty || state.isLoading)
                    if state.isLoading { ProgressView() }
                }
                if state.isConfigured {
                    Section {
                        Button("Disconnetti questo iPad", role: .destructive) {
                            state.disconnect(); if isSheet { dismiss() }
                        }
                    }
                }
            }
            .navigationTitle("Connessione")
            .onAppear {
                url = state.serverURL
                token = state.token
            }
        }
    }
}
