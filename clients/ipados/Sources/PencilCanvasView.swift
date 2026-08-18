import SwiftUI
import PencilKit

struct PencilCanvasView: UIViewRepresentable {
    @Binding var drawingData: Data

    func makeCoordinator() -> Coordinator { Coordinator(drawingData: $drawingData) }

    func makeUIView(context: Context) -> PKCanvasView {
        let canvas = PKCanvasView()
        canvas.drawingPolicy = .anyInput
        canvas.tool = PKInkingTool(.pen, color: .label, width: 2.5)
        canvas.backgroundColor = .systemBackground
        canvas.delegate = context.coordinator
        if let drawing = try? PKDrawing(data: drawingData) { canvas.drawing = drawing }
        return canvas
    }

    func updateUIView(_ uiView: PKCanvasView, context: Context) {
        if uiView.drawing.dataRepresentation() != drawingData,
           let drawing = try? PKDrawing(data: drawingData) {
            uiView.drawing = drawing
        }
    }

    final class Coordinator: NSObject, PKCanvasViewDelegate {
        @Binding var drawingData: Data
        init(drawingData: Binding<Data>) { _drawingData = drawingData }
        func canvasViewDrawingDidChange(_ canvasView: PKCanvasView) {
            drawingData = canvasView.drawing.dataRepresentation()
        }
    }
}
