import SwiftUI

struct StudioView: View {
    @EnvironmentObject var state: AppState
    @State private var pdfData: Data?
    @State private var currentPage = 1
    @State private var question = ""
    @State private var tutorAnswer = ""
    @State private var isAsking = false
    @State private var drawingData = Data()
    @State private var rightTab = 0

    var body: some View {
        HSplitView {
            documentPane
                .frame(minWidth: 520)
            VStack(spacing: 0) {
                Picker("Pannello", selection: $rightTab) {
                    Text("Tutor").tag(0)
                    Text("Quaderno").tag(1)
                }
                .pickerStyle(.segmented)
                .padding()

                if rightTab == 0 { tutorPane }
                else { notebookPane }
            }
            .frame(minWidth: 360, idealWidth: 430)
        }
        .task(id: state.selectedDocument?.id) { await loadPDF() }
    }

    private var documentPane: some View {
        VStack(spacing: 0) {
            HStack {
                if let document = state.selectedDocument {
                    Text(document.name).font(.headline).lineLimit(1)
                } else { Text("Nessun documento").foregroundStyle(.secondary) }
                Spacer()
                Text("Pagina \(currentPage)").font(.caption).foregroundStyle(.secondary)
            }
            .padding(.horizontal).padding(.vertical, 10)
            Divider()
            Group {
                if let pdfData { PDFDocumentView(data: pdfData, currentPage: $currentPage) }
                else if state.selectedDocument == nil {
                    ContentUnavailableView("Seleziona un documento", systemImage: "doc.text")
                } else {
                    ProgressView("Caricamento PDF…")
                }
            }
        }
    }

    private var tutorPane: some View {
        VStack(spacing: 12) {
            ScrollView {
                if tutorAnswer.isEmpty {
                    ContentUnavailableView("Tutor contestuale", systemImage: "graduationcap", description: Text("Chiedi spiegazioni sul documento aperto."))
                } else {
                    Text(tutorAnswer).frame(maxWidth: .infinity, alignment: .leading).textSelection(.enabled).padding()
                }
            }
            Divider()
            HStack(alignment: .bottom) {
                TextField("Chiedi al tutor…", text: $question, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(1...5)
                Button {
                    Task { await askTutor() }
                } label: {
                    if isAsking { ProgressView() } else { Image(systemName: "arrow.up.circle.fill").font(.title2) }
                }
                .disabled(question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isAsking)
            }
            .padding()
        }
    }

    private var notebookPane: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Foglio libero").font(.headline)
                Spacer()
                Button("Pulisci") { drawingData = Data() }
            }
            .padding()
            Divider()
            PencilCanvasView(drawingData: $drawingData)
        }
    }

    private func loadPDF() async {
        pdfData = nil
        guard state.selectedDocument != nil else { return }
        do { pdfData = try await state.loadSelectedPDF() }
        catch { state.errorMessage = error.localizedDescription }
    }

    private func askTutor() async {
        let prompt = question.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !prompt.isEmpty else { return }
        isAsking = true
        defer { isAsking = false }
        do {
            let contextual = "Sto leggendo la pagina \(currentPage) del documento aperto. \(prompt)"
            let response = try await state.ask(contextual)
            tutorAnswer = response.content
            question = ""
        } catch { state.errorMessage = error.localizedDescription }
    }
}
