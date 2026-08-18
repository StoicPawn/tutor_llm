import Foundation
import SwiftData

@Model
final class CachedSyncEntity {
    @Attribute(.unique) var key: String
    var workspaceID: Int
    var entityType: String
    var clientUUID: String
    var serverID: Int?
    var revision: Int
    var deleted: Bool
    var payload: Data
    var dirty: Bool
    var conflict: Bool
    var updatedAt: Date

    init(workspaceID: Int, entityType: String, clientUUID: String, serverID: Int? = nil, revision: Int = 0,
         deleted: Bool = false, payload: Data = Data(), dirty: Bool = false, conflict: Bool = false) {
        self.workspaceID = workspaceID
        self.entityType = entityType
        self.clientUUID = clientUUID
        self.serverID = serverID
        self.revision = revision
        self.deleted = deleted
        self.payload = payload
        self.dirty = dirty
        self.conflict = conflict
        self.updatedAt = Date()
        self.key = "\(workspaceID):\(entityType):\(clientUUID)"
    }
}

@Model
final class CachedWorkspaceState {
    @Attribute(.unique) var workspaceID: Int
    var cursor: Int
    var manifestRevision: String
    var lastSyncAt: Date?

    init(workspaceID: Int) {
        self.workspaceID = workspaceID
        self.cursor = 0
        self.manifestRevision = ""
    }
}

@Model
final class CachedDocumentFile {
    @Attribute(.unique) var key: String
    var workspaceID: Int
    var documentID: Int
    var name: String
    var localPath: String
    var downloadedAt: Date

    init(workspaceID: Int, documentID: Int, name: String, localPath: String) {
        self.workspaceID = workspaceID
        self.documentID = documentID
        self.name = name
        self.localPath = localPath
        self.downloadedAt = Date()
        self.key = "\(workspaceID):\(documentID)"
    }
}

@MainActor
final class ClientCacheStore: ObservableObject {
    let container: ModelContainer
    private var context: ModelContext { container.mainContext }
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    init(inMemory: Bool = false) {
        let config = ModelConfiguration(isStoredInMemoryOnly: inMemory)
        self.container = try! ModelContainer(for: CachedSyncEntity.self, CachedWorkspaceState.self, CachedDocumentFile.self, configurations: config)
    }

    func state(for workspaceID: Int) -> CachedWorkspaceState {
        let descriptor = FetchDescriptor<CachedWorkspaceState>(predicate: #Predicate { $0.workspaceID == workspaceID })
        if let current = try? context.fetch(descriptor).first { return current }
        let value = CachedWorkspaceState(workspaceID: workspaceID)
        context.insert(value)
        try? context.save()
        return value
    }

    func cachedDocument(workspaceID: Int, documentID: Int) -> URL? {
        let key = "\(workspaceID):\(documentID)"
        let descriptor = FetchDescriptor<CachedDocumentFile>(predicate: #Predicate { $0.key == key })
        guard let item = try? context.fetch(descriptor).first else { return nil }
        let url = URL(fileURLWithPath: item.localPath)
        return FileManager.default.fileExists(atPath: url.path) ? url : nil
    }

    func saveDocument(data: Data, workspaceID: Int, documentID: Int, name: String) throws -> URL {
        let root = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
            .appendingPathComponent("TutorLLM/Documents/\(workspaceID)", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let safeName = name.replacingOccurrences(of: "/", with: "_")
        let url = root.appendingPathComponent("\(documentID)-\(safeName)")
        try data.write(to: url, options: .atomic)
        let key = "\(workspaceID):\(documentID)"
        let descriptor = FetchDescriptor<CachedDocumentFile>(predicate: #Predicate { $0.key == key })
        if let existing = try? context.fetch(descriptor).first {
            existing.localPath = url.path; existing.name = name; existing.downloadedAt = Date()
        } else {
            context.insert(CachedDocumentFile(workspaceID: workspaceID, documentID: documentID, name: name, localPath: url.path))
        }
        try context.save()
        return url
    }

    func queueChange(workspaceID: Int, entityType: String, clientUUID: String = UUID().uuidString,
                     serverID: Int? = nil, baseRevision: Int = 0, payload: [String: Any], deleted: Bool = false) throws -> String {
        let key = "\(workspaceID):\(entityType):\(clientUUID)"
        let data = try JSONSerialization.data(withJSONObject: payload)
        let descriptor = FetchDescriptor<CachedSyncEntity>(predicate: #Predicate { $0.key == key })
        if let existing = try context.fetch(descriptor).first {
            existing.payload = data; existing.deleted = deleted; existing.dirty = true; existing.conflict = false; existing.updatedAt = Date()
        } else {
            context.insert(CachedSyncEntity(workspaceID: workspaceID, entityType: entityType, clientUUID: clientUUID,
                                            serverID: serverID, revision: baseRevision, deleted: deleted, payload: data, dirty: true))
        }
        try context.save()
        return clientUUID
    }

    func dirtyEntities(workspaceID: Int) -> [CachedSyncEntity] {
        let descriptor = FetchDescriptor<CachedSyncEntity>(predicate: #Predicate { $0.workspaceID == workspaceID && $0.dirty == true })
        return (try? context.fetch(descriptor)) ?? []
    }

    func applyRemote(_ object: SyncObject) throws {
        let key = "\(object.workspace_id):\(object.entity_type):\(object.client_uuid)"
        let descriptor = FetchDescriptor<CachedSyncEntity>(predicate: #Predicate { $0.key == key })
        let data = try JSONSerialization.data(withJSONObject: object.payload.value)
        if let local = try context.fetch(descriptor).first {
            guard !local.dirty else { return }
            local.serverID = object.server_id; local.revision = object.revision; local.deleted = object.deleted
            local.payload = data; local.conflict = false; local.updatedAt = Date()
        } else {
            context.insert(CachedSyncEntity(workspaceID: object.workspace_id, entityType: object.entity_type,
                                            clientUUID: object.client_uuid, serverID: object.server_id, revision: object.revision,
                                            deleted: object.deleted, payload: data))
        }
        try context.save()
    }

    func markApplied(_ local: CachedSyncEntity, server: SyncObject) throws {
        local.serverID = server.server_id; local.revision = server.revision; local.deleted = server.deleted
        local.dirty = false; local.conflict = false; local.updatedAt = Date()
        try context.save()
    }

    func markConflict(_ local: CachedSyncEntity) throws {
        local.conflict = true
        try context.save()
    }
}
