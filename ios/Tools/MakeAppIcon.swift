// Draws the app icon. Run it whenever the mark changes; the PNG it writes is what
// ships in the asset catalog, so the icon stays reproducible from source rather than
// being a binary someone once exported by hand.
//
//   swift Tools/MakeAppIcon.swift \
//     PMThinkingCoach/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png
//
// The mark is a decision fork: one path in, two ways out, one of them taken. Only the
// 1024pt master is committed — Xcode derives every other size from it.

import AppKit
import CoreGraphics
import Foundation

let size: CGFloat = 1024
let colorSpace = CGColorSpaceCreateDeviceRGB()

guard let ctx = CGContext(
    data: nil, width: Int(size), height: Int(size), bitsPerComponent: 8,
    bytesPerRow: 0, space: colorSpace,
    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
) else { fatalError("no context") }

func rgb(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat, _ a: CGFloat = 1) -> CGColor {
    CGColor(colorSpace: colorSpace, components: [r / 255, g / 255, b / 255, a])!
}

// Flip to a top-left origin so the coordinates below read like the design.
ctx.translateBy(x: 0, y: size)
ctx.scaleBy(x: 1, y: -1)

// MARK: Background — diagonal indigo gradient, full bleed (iOS masks the corners).
let bg = CGGradient(
    colorsSpace: colorSpace,
    colors: [rgb(28, 36, 84), rgb(46, 71, 133), rgb(76, 111, 208)] as CFArray,
    locations: [0, 0.55, 1]
)!
ctx.drawLinearGradient(
    bg, start: CGPoint(x: 0, y: 0), end: CGPoint(x: size, y: size), options: []
)

// Soft highlight in the upper-left so the surface has depth at large sizes.
let glow = CGGradient(
    colorsSpace: colorSpace,
    colors: [rgb(255, 255, 255, 0.20), rgb(255, 255, 255, 0)] as CFArray,
    locations: [0, 1]
)!
ctx.drawRadialGradient(
    glow,
    startCenter: CGPoint(x: 300, y: 250), startRadius: 0,
    endCenter: CGPoint(x: 300, y: 250), endRadius: 620,
    options: []
)

// MARK: Fork
let white = rgb(255, 255, 255)
let dim = rgb(255, 255, 255, 0.38)
let solidDim = rgb(255, 255, 255, 1)
let spark = rgb(255, 199, 120)

let stroke: CGFloat = 56
ctx.setLineCap(.round)
ctx.setLineJoin(.round)

// Everything lives inside a centred 700pt box so the corner mask never clips it.
let root = CGPoint(x: 512, y: 776)
let split = CGPoint(x: 512, y: 548)
let leftEnd = CGPoint(x: 322, y: 356)
let rightEnd = CGPoint(x: 702, y: 356)

// Left branch and its node are drawn in one transparency layer so the overlap
// between them does not read as a denser blob.
ctx.setAlpha(0.34)
ctx.beginTransparencyLayer(auxiliaryInfo: nil)
ctx.setStrokeColor(solidDim)
ctx.setFillColor(solidDim)
ctx.setLineWidth(stroke)
ctx.beginPath()
ctx.move(to: split)
ctx.addCurve(
    to: leftEnd,
    control1: CGPoint(x: 512, y: 448),
    control2: CGPoint(x: 322, y: 432)
)
ctx.strokePath()
ctx.fillEllipse(in: CGRect(x: leftEnd.x - 46, y: leftEnd.y - 46, width: 92, height: 92))
ctx.endTransparencyLayer()
ctx.setAlpha(1)

// Stem + chosen branch, drawn as one continuous path.
ctx.setStrokeColor(white)
ctx.setLineWidth(stroke)
ctx.beginPath()
ctx.move(to: root)
ctx.addLine(to: split)
ctx.addCurve(
    to: rightEnd,
    control1: CGPoint(x: 512, y: 448),
    control2: CGPoint(x: 702, y: 432)
)
ctx.strokePath()

// Start node.
ctx.setFillColor(white)
ctx.fillEllipse(in: CGRect(x: root.x - 46, y: root.y - 46, width: 92, height: 92))

// The decision — filled, warm, ringed so it still holds at 60pt.
ctx.setFillColor(spark)
ctx.fillEllipse(in: CGRect(x: rightEnd.x - 88, y: rightEnd.y - 88, width: 176, height: 176))
ctx.setStrokeColor(rgb(255, 255, 255, 0.92))
ctx.setLineWidth(22)
ctx.strokeEllipse(in: CGRect(x: rightEnd.x - 88, y: rightEnd.y - 88, width: 176, height: 176))

// A checkmark inside the chosen node.
ctx.setStrokeColor(rgb(28, 36, 84))
ctx.setLineWidth(30)
ctx.beginPath()
ctx.move(to: CGPoint(x: rightEnd.x - 38, y: rightEnd.y + 2))
ctx.addLine(to: CGPoint(x: rightEnd.x - 9, y: rightEnd.y + 32))
ctx.addLine(to: CGPoint(x: rightEnd.x + 42, y: rightEnd.y - 30))
ctx.strokePath()

guard let image = ctx.makeImage() else { fatalError("no image") }
let rep = NSBitmapImageRep(cgImage: image)
rep.size = NSSize(width: size, height: size)
guard let data = rep.representation(using: .png, properties: [:]) else { fatalError("no png") }

let out = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "AppIcon.png"
try data.write(to: URL(fileURLWithPath: out))
print("wrote \(out) (\(data.count) bytes)")
