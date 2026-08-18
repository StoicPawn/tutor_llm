import SwiftUI
import PDFKit

struct PDFDocumentView: UIViewRepresentable {
    let data: Data
    @Binding var currentPage: Int

    func makeCoordinator() -> Coordinator { Coordinator(currentPage: $currentPage) }

    func makeUIView(context: Context) -> PDFView {
        let view = PDFView()
        view.autoScales = true
        view.displayMode = .singlePageContinuous
        view.displayDirection = .vertical
        view.displaysPageBreaks = true
        view.backgroundColor = .secondarySystemBackground
        view.document = PDFDocument(data: data)
        NotificationCenter.default.addObserver(
            context.coordinator,
            selector: #selector(Coordinator.pageChanged(_:)),
            name: Notification.Name.PDFViewPageChanged,
            object: view
        )
        return view
    }

    func updateUIView(_ uiView: PDFView, context: Context) {
        if let page = uiView.document?.page(at: max(0, currentPage - 1)), uiView.currentPage != page {
            uiView.go(to: page)
        }
    }

    final class Coordinator: NSObject {
        @Binding var currentPage: Int
        init(currentPage: Binding<Int>) { _currentPage = currentPage }

        @objc func pageChanged(_ note: Notification) {
            guard let view = note.object as? PDFView,
                  let page = view.currentPage,
                  let index = view.document?.index(for: page) else { return }
            currentPage = index + 1
        }
    }
}
