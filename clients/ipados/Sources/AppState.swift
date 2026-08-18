import Foundation
import SwiftUI

@MainActor
final class AppState: ObservableObject {
    @Published var serverURL = ""
    @Published var token = ""
    @Published var isConfigured = false
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var health: HealthResponse?
    @Published var workspaces: [Workspace] = []
    @Published var selectedWorkspace: Workspace?
    @Published var documents: [DocumentItem] = []
    @Published var selectedDocument: DocumentItem?

    private var api: APIClient?

    init() {
        serverURL = UserDefaults.standard.string(forKey: "serverURL") ?? ""
        token = KeychainStore.read("deviceToken") ?? ""
        isConfigured = !serverURL.isEmpty
        if let url = URL(string: serverURL), isConfigured {
            api = APIClient(baseURL: url, token: token)
        }
    }

    func configure(serverURL: String, token: String) async {
        let normalized = serverURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: normalized), url.scheme != nil else {
            errorMessage = "Inserisci un URL server valido."
            return
        }
        isLoading = true
        defer { isLoading = false }
        let candidate = APIClient(baseURL: url, token: token)
        do {
            let health = try await candidate.health()
            if health.auth_required && token.isEmpty { throw APIClient.APIError.server(401, "Token dispositivo richiesto.") }
            if health.auth_required { _ = try await candidate.identity() }
            self.serverURL = normalized
            self.token = token
            self.api = candidate
            self.health = health
            self.isConfigured = true
            UserDefaults.standard.set(normalized, forKey: "serverURL")
            try KeychainStore.save(token, key: "deviceToken")
            await reloadWorkspaces()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func disconnect() {
        serverURL = ""; token = ""; isConfigured = false; api = nil
        workspaces = []; selectedWorkspace = nil; documents = []; selectedDocument = nil
        UserDefaults.standard.removeObject(forKey: "serverURL")
        KeychainStore.delete("deviceToken")
    }

    func reloadWorkspaces() async {
        guard let api else { return }
        isLoading = true
        defer { isLoading = false }
        do {
            workspaces = try await api.workspaces()
            if selectedWorkspace == nil { selectedWorkspace = workspaces.first }
            if let selectedWorkspace { await loadDocuments(workspace: selectedWorkspace) }
        } catch { errorMessage = error.localizedDescription }
    }

    func select(workspace: Workspace) async {
        selectedWorkspace = workspace
        selectedDocument = nil
        await loadDocuments(workspace: workspace)
    }

    func loadDocuments(workspace: Workspace) async {
        guard let api else { return }
        do {
            documents = try await api.documents(workspaceID: workspace.id)
            if selectedDocument == nil { selectedDocument = documents.first }
        } catch { errorMessage = error.localizedDescription }
    }

    func ask(_ text: String, mode: String = "Tutor") async throws -> TutorResponse {
        guard let api, let workspace = selectedWorkspace else { throw APIClient.APIError.invalidResponse }
        return try await api.ask(workspaceID: workspace.id, question: text, documentIDs: selectedDocument.map { [$0.id] }, mode: mode)
    }

    func loadSelectedPDF() async throws -> Data {
        guard let api, let workspace = selectedWorkspace, let document = selectedDocument else { throw APIClient.APIError.invalidResponse }
        return try await api.sourceDocument(workspaceID: workspace.id, documentID: document.id)
    }
}
