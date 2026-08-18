import Foundation

struct Workspace: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
    let description: String?
    let goal: String?
}

struct DocumentItem: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
    let created_at: String?
}

struct TutorResponse: Codable {
    let content: String
    let sources: [SourceRef]
}

struct SourceRef: Codable, Hashable {
    let document_id: Int?
    let document_name: String?
    let page: Int?
    let chunk_id: Int?
    let text: String?
}

struct DeviceIdentity: Codable {
    let auth_type: String?
    let device: DeviceInfo?
}

struct DeviceInfo: Codable {
    let id: Int
    let name: String
    let platform: String
    let token_prefix: String?
    let last_seen_at: String?
}

struct SyncManifest: Codable {
    let workspace_id: Int
    let revision: String
}

struct HealthResponse: Codable {
    let ok: Bool
    let service: String
    let api_version: String
    let deploy_mode: String
    let inference_provider: String
    let chat_model: String
    let embedding_model: String
    let inference_ready: Bool
    let auth_required: Bool
}

struct TutorAskRequest: Codable {
    let workspace_id: Int
    let topic: String
    let document_ids: [Int]?
    let epistemic_mode: String
}
