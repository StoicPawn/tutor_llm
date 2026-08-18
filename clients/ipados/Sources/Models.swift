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

struct NotebookSummary: Codable, Identifiable {
    let id: Int
    let workspace_id: Int
    let title: String
    let description: String?
    let linked_document_id: Int?
    let linked_page: Int?
    let linked_concept: String?
    let page_count: Int?
}

struct NotebookPage: Codable, Identifiable {
    let id: Int
    let notebook_id: Int
    let position: Int
    let title: String
    let width: Double
    let height: Double
    let background: String
    let layers: [JSONValue]
}

struct NotebookDetail: Codable, Identifiable {
    let id: Int
    let workspace_id: Int
    let title: String
    let linked_document_id: Int?
    let linked_page: Int?
    let linked_concept: String?
    let pages: [NotebookPage]
}

enum JSONValue: Codable {
    case string(String), number(Double), bool(Bool), object([String: JSONValue]), array([JSONValue]), null

    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .null }
        else if let v = try? c.decode(Bool.self) { self = .bool(v) }
        else if let v = try? c.decode(Double.self) { self = .number(v) }
        else if let v = try? c.decode(String.self) { self = .string(v) }
        else if let v = try? c.decode([String: JSONValue].self) { self = .object(v) }
        else { self = .array(try c.decode([JSONValue].self)) }
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self {
        case .string(let v): try c.encode(v)
        case .number(let v): try c.encode(v)
        case .bool(let v): try c.encode(v)
        case .object(let v): try c.encode(v)
        case .array(let v): try c.encode(v)
        case .null: try c.encodeNil()
        }
    }

    static func from(any: Any) -> JSONValue {
        switch any {
        case let v as String: return .string(v)
        case let v as Bool: return .bool(v)
        case let v as NSNumber: return .number(v.doubleValue)
        case let v as [String: Any]: return .object(v.mapValues { from(any: $0) })
        case let v as [Any]: return .array(v.map { from(any: $0) })
        default: return .null
        }
    }

    var value: Any {
        switch self {
        case .string(let v): return v
        case .number(let v): return v
        case .bool(let v): return v
        case .object(let v): return v.mapValues { $0.value }
        case .array(let v): return v.map { $0.value }
        case .null: return NSNull()
        }
    }
}

struct SyncObject: Codable {
    let workspace_id: Int
    let entity_type: String
    let client_uuid: String
    let server_id: Int?
    let revision: Int
    let deleted: Bool
    let payload: JSONValue
    let updated_at: String?
}

struct SyncChange: Codable {
    let seq: Int
    let operation: String
    let object: SyncObject?
}

struct SyncPullResponse: Codable {
    let workspace_id: Int
    let since: Int
    let cursor: Int
    let changes: [SyncChange]
}

struct SyncPushRequest: Codable {
    let workspace_id: Int
    let entity_type: String
    let client_uuid: String
    let base_revision: Int
    let payload: JSONValue
    let deleted: Bool
    let server_id: Int?
}

struct SyncPushResponse: Codable {
    let status: String
    let object: SyncObject?
    let server: SyncObject?
    let expected_revision: Int?
}
