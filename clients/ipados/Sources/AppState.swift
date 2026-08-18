import Foundation
import SwiftUI

@MainActor
final class AppState: ObservableObject {
    @Published var serverURL = ""
    @Published var token = ""
    @Published var isConfigured = false
    @Published var isLoading = false
    @Published var isSyncing = false
    @Published var errorMessage: String?
    @Published var health: HealthResponse?
    @Published var workspaces: [Workspace] = []
    @Published var selectedWorkspace: Workspace?
    @Published var documents: [DocumentItem] = []
    @Published var selectedDocument: DocumentItem?
    @Published var lastSyncAt: Date?
    @Published var conflictCount = 0

    let cache = ClientCacheStore()
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
            if let selectedWorkspace {
                await loadDocuments(workspace: selectedWorkspace)
                await syncNow()
            }
        } catch { errorMessage = error.localizedDescription }
    }

    func select(workspace: Workspace) async {
        selectedWorkspace = workspace
        selectedDocument = nil
        await loadDocuments(workspace: workspace)
        await syncNow()
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

    func selectedPDFURL() async throws -> URL {
        guard let workspace = selectedWorkspace, let document = selectedDocument else { throw APIClient.APIError.invalidResponse }
        if let local = cache.cachedDocument(workspaceID: workspace.id, documentID: document.id) { return local }
        guard let api else { throw APIClient.APIError.invalidResponse }
        let data = try await api.sourceDocument(workspaceID: workspace.id, documentID: document.id)
        return try cache.saveDocument(data: data, workspaceID: workspace.id, documentID: document.id, name: document.name)
    }

    func makeSelectedDocumentAvailableOffline() async {
        do { _ = try await selectedPDFURL() }
        catch { errorMessage = error.localizedDescription }
    }

    func isSelectedDocumentOffline() -> Bool {
        guard let workspace = selectedWorkspace, let document = selectedDocument else { return false }
        return cache.cachedDocument(workspaceID: workspace.id, documentID: document.id) != nil
    }

    func queueOfflineChange(entityType: String, clientUUID: String = UUID().uuidString,
                            serverID: Int? = nil, baseRevision: Int = 0,
                            payload: [String: Any], deleted: Bool = false) throws -> String {
        guard let workspace = selectedWorkspace else { throw APIClient.APIError.invalidResponse }
        return try cache.queueChange(workspaceID: workspace.id, entityType: entityType, clientUUID: clientUUID,
                                     serverID: serverID, baseRevision: baseRevision, payload: payload, deleted: deleted)
    }

    func syncNow() async {
        guard let api, let workspace = selectedWorkspace, !isSyncing else { return }
        isSyncing = true
        defer { isSyncing = false }
        do {
            let localState = cache.state(for: workspace.id)
            let pulled = try await api.syncPull(workspaceID: workspace.id, since: localState.cursor)
            for change in pulled.changes {
                if let object = change.object { try cache.applyRemote(object) }
            }
            localState.cursor = pulled.cursor

            for local in cache.dirtyEntities(workspaceID: workspace.id) {
                let object = try JSONSerialization.jsonObject(with: local.payload)
                let json = JSONValue.from(any: object)
                let response = try await api.syncPush(SyncPushRequest(
                    workspace_id: workspace.id, entity_type: local.entityType, client_uuid: local.clientUUID,
                    base_revision: local.revision, payload: json, deleted: local.deleted, server_id: local.serverID
                ))
                if response.status == "applied", let server = response.object {
                    try cache.markApplied(local, server: server)
                } else if response.status == "conflict" {
                    try cache.markConflict(local)
                }
            }

            let manifest = try await api.manifest(workspaceID: workspace.id)
            localState.manifestRevision = manifest.revision
            localState.lastSyncAt = Date()
            lastSyncAt = localState.lastSyncAt
            conflictCount = cache.dirtyEntities(workspaceID: workspace.id).filter(\.conflict).count
            try cache.save()
        } catch {
            // Offline is expected: cached PDFs and dirty artifacts remain usable.
            errorMessage = error.localizedDescription
        }
    }
}
