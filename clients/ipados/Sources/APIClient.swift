import Foundation

actor APIClient {
    enum APIError: LocalizedError {
        case invalidURL
        case invalidResponse
        case server(Int, String)

        var errorDescription: String? {
            switch self {
            case .invalidURL: return "URL server non valida."
            case .invalidResponse: return "Risposta server non valida."
            case let .server(code, message): return "Server \(code): \(message)"
            }
        }
    }

    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()
    private var baseURL: URL
    private var token: String

    init(baseURL: URL, token: String) {
        self.baseURL = baseURL
        self.token = token
    }

    func reconfigure(baseURL: URL, token: String) {
        self.baseURL = baseURL
        self.token = token
    }

    private func request(_ path: String, method: String = "GET", body: Data? = nil) async throws -> (Data, HTTPURLResponse) {
        guard let url = URL(string: path, relativeTo: baseURL) else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 120
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if !token.isEmpty { request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else {
            let message = (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["detail"] as? String
            throw APIError.server(http.statusCode, message ?? String(data: data, encoding: .utf8) ?? "Errore")
        }
        return (data, http)
    }

    func health() async throws -> HealthResponse {
        let (data, _) = try await request("/health")
        return try decoder.decode(HealthResponse.self, from: data)
    }

    func identity() async throws -> DeviceIdentity {
        let (data, _) = try await request("/device/me")
        return try decoder.decode(DeviceIdentity.self, from: data)
    }

    func workspaces() async throws -> [Workspace] {
        let (data, _) = try await request("/workspaces")
        return try decoder.decode([Workspace].self, from: data)
    }

    func documents(workspaceID: Int) async throws -> [DocumentItem] {
        let (data, _) = try await request("/workspaces/\(workspaceID)/documents")
        return try decoder.decode([DocumentItem].self, from: data)
    }

    func ask(workspaceID: Int, question: String, documentIDs: [Int]? = nil, mode: String = "Tutor") async throws -> TutorResponse {
        let payload = TutorAskRequest(workspace_id: workspaceID, topic: question, document_ids: documentIDs, epistemic_mode: mode)
        let body = try encoder.encode(payload)
        let (data, _) = try await request("/tutor/ask", method: "POST", body: body)
        return try decoder.decode(TutorResponse.self, from: data)
    }

    func sourceDocument(workspaceID: Int, documentID: Int) async throws -> Data {
        let (data, _) = try await request("/workspaces/\(workspaceID)/documents/\(documentID)/source")
        return data
    }

    func notebooks(workspaceID: Int) async throws -> [NotebookSummary] {
        let (data, _) = try await request("/workspaces/\(workspaceID)/notebooks")
        return try decoder.decode([NotebookSummary].self, from: data)
    }

    func notebook(workspaceID: Int, notebookID: Int) async throws -> NotebookDetail {
        let (data, _) = try await request("/workspaces/\(workspaceID)/notebooks/\(notebookID)")
        return try decoder.decode(NotebookDetail.self, from: data)
    }

    func createNotebook(workspaceID: Int, title: String, documentID: Int?, page: Int? = nil) async throws -> Int {
        struct Request: Codable {
            let workspace_id: Int
            let title: String
            let linked_document_id: Int?
            let linked_page: Int?
            let concept: String
        }
        struct Response: Codable { let id: Int }
        let payload = Request(workspace_id: workspaceID, title: title, linked_document_id: documentID, linked_page: page, concept: "")
        let (data, _) = try await request("/notebooks", method: "POST", body: try encoder.encode(payload))
        return try decoder.decode(Response.self, from: data).id
    }

    func manifest(workspaceID: Int) async throws -> SyncManifest {
        let (data, _) = try await request("/sync/workspaces/\(workspaceID)/manifest")
        return try decoder.decode(SyncManifest.self, from: data)
    }

    func syncPull(workspaceID: Int, since: Int, limit: Int = 500) async throws -> SyncPullResponse {
        let (data, _) = try await request("/sync/workspaces/\(workspaceID)/changes?since=\(since)&limit=\(limit)")
        return try decoder.decode(SyncPullResponse.self, from: data)
    }

    func syncPush(_ payload: SyncPushRequest) async throws -> SyncPushResponse {
        let body = try encoder.encode(payload)
        let (data, _) = try await request("/sync/push", method: "POST", body: body)
        return try decoder.decode(SyncPushResponse.self, from: data)
    }

    func syncResolve(workspaceID: Int, entityType: String, clientUUID: String, serverRevision: Int,
                     payload: JSONValue, deleted: Bool = false) async throws -> SyncPushResponse {
        struct ResolveRequest: Codable {
            let workspace_id: Int
            let entity_type: String
            let client_uuid: String
            let server_revision: Int
            let payload: JSONValue
            let deleted: Bool
        }
        let req = ResolveRequest(workspace_id: workspaceID, entity_type: entityType, client_uuid: clientUUID,
                                 server_revision: serverRevision, payload: payload, deleted: deleted)
        let body = try encoder.encode(req)
        let (data, _) = try await request("/sync/resolve", method: "POST", body: body)
        return try decoder.decode(SyncPushResponse.self, from: data)
    }
}
