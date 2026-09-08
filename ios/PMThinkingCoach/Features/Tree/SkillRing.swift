import SwiftUI

/// One cell of the map: a domain sector crossed with a tier ring.
///
/// Drawn as an individual view rather than as one painted canvas so each cell can carry
/// its own hit target and its own VoiceOver label — the map has to be navigable without
/// sight, and 18 shapes is cheap (spec v0.2 §14).
struct AnnularSector: Shape {
    let startAngle: Angle
    let endAngle: Angle
    let innerRadius: CGFloat
    let outerRadius: CGFloat
    /// Gap in points between neighbouring cells, so the grid reads as separate blocks.
    var inset: CGFloat = 3

    func path(in rect: CGRect) -> Path {
        let center = CGPoint(x: rect.midX, y: rect.midY)
        let outer = max(0, outerRadius - inset / 2)
        let inner = max(0, innerRadius + inset / 2)
        // Convert the linear gap into an angular one so cells stay parallel-sided.
        let padOuter = Angle(radians: Double(inset / max(outer, 1)) / 2)
        let padInner = Angle(radians: Double(inset / max(inner, 1)) / 2)

        var path = Path()
        path.addArc(
            center: center, radius: outer,
            startAngle: startAngle + padOuter, endAngle: endAngle - padOuter,
            clockwise: false
        )
        path.addArc(
            center: center, radius: inner,
            startAngle: endAngle - padInner, endAngle: startAngle + padInner,
            clockwise: true
        )
        path.closeSubpath()
        return path
    }
}

/// The whole map. Sectors are domains, rings are tiers, exactly as in the source.
struct SkillRingMap: View {
    let tree: TreeResponse
    let highlighted: String?
    let onSelect: (BlockSummary) -> Void

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var appeared = false

    private var sweep: Double { 360 / Double(max(tree.domains.count, 1)) }

    /// One hue per domain. Status changes how strongly a cell is filled, but the hue
    /// stays — otherwise a mostly-locked map reads as one grey disc and stops being
    /// the promise it is supposed to be.
    ///
    /// Recomputed for the sand ground: each gives ≥ 4.5:1 on it and sits far enough
    /// from the green accent in hue. `economics` and `ai_systems` used to be green and
    /// read as «passed» on this palette, so they moved to olive and yellow-green.
    /// Hues repeat across the two trees on purpose: the switcher never shows both.
    /// One hue per domain. Status changes how strongly a cell is filled, but the hue
    /// stays — otherwise a mostly-locked map reads as one grey disc and stops being
    /// the promise it is supposed to be.
    ///
    /// Values are the same list as `HUES` in `web/src/views/skilltree.js`: recomputed
    /// for the sand ground, each ≥ 4.5:1 on it and far enough from the green accent.
    /// **The two lists must stay in step** — it is the same map on two clients.
    private static let domainHues: [String: Color] = [
        "discovery": Color(red: 0.184, green: 0.435, blue: 0.659),   // #2f6fa8
        "value_design": Color(red: 0.416, green: 0.353, blue: 0.659),   // #6a5aa8
        "delivery": Color(red: 0.122, green: 0.498, blue: 0.475),   // #1f7f79
        "marketing": Color(red: 0.659, green: 0.357, blue: 0.094),   // #a85b18
        "growth": Color(red: 0.698, green: 0.290, blue: 0.388),   // #b24a63
        "economics": Color(red: 0.486, green: 0.420, blue: 0.133),   // #7c6b22
        "data": Color(red: 0.169, green: 0.478, blue: 0.620),   // #2b7a9e
        "integration": Color(red: 0.361, green: 0.369, blue: 0.659),   // #5c5ea8
        "scale": Color(red: 0.659, green: 0.353, blue: 0.220),   // #a85a38
        "performance": Color(red: 0.541, green: 0.404, blue: 0.071),   // #8a6712
        "ai_systems": Color(red: 0.373, green: 0.478, blue: 0.149),   // #5f7a26
        "security": Color(red: 0.639, green: 0.282, blue: 0.420),   // #a3486b
    ]

    private func hue(_ block: BlockSummary) -> Color {
        Self.domainHues[block.domainKey] ?? Theme.Palette.accent
    }

    var body: some View {
        GeometryReader { geometry in
            let side = min(geometry.size.width, geometry.size.height)
            let outer = side / 2
            let ringWidth = (outer - Theme.Spacing.xl - Theme.Spacing.l) / 3

            ZStack {
                ForEach(Array(tree.domains.enumerated()), id: \.element.key) { index, domain in
                    ForEach(tree.blocks(inDomain: domain.key)) { block in
                        cell(
                            block: block,
                            domainIndex: index,
                            ringWidth: ringWidth,
                            centreHole: Theme.Spacing.xl
                        )
                    }
                    domainLabel(domain, index: index, radius: outer - Theme.Spacing.s)
                }
                centre
            }
            .frame(width: side, height: side)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .aspectRatio(1, contentMode: .fit)
        .onAppear {
            guard !appeared else { return }
            if reduceMotion { appeared = true } else {
                withAnimation(Motion.standard) { appeared = true }
            }
        }
    }

    private func cell(
        block: BlockSummary, domainIndex: Int, ringWidth: CGFloat, centreHole: CGFloat
    ) -> some View {
        // Start at the top and go clockwise, so the trunk reads like a clock face.
        let start = Angle(degrees: Double(domainIndex) * sweep - 90)
        let end = Angle(degrees: Double(domainIndex + 1) * sweep - 90)
        let inner = centreHole + ringWidth * CGFloat(block.tier - 1)
        let outer = centreHole + ringWidth * CGFloat(block.tier)
        let shape = AnnularSector(
            startAngle: start, endAngle: end, innerRadius: inner, outerRadius: outer
        )
        let isHighlighted = highlighted == block.id

        return shape
            .fill(fill(for: block))
            .overlay(shape.stroke(stroke(for: block), lineWidth: isHighlighted ? 2 : 0.75))
            .overlay(alignment: .center) {
                marker(
                    S.Tree.statusSymbol(block.status),
                    tint: markerTint(block),
                    at: start, end: end, inner: inner, outer: outer
                )
            }
            .scaleEffect(appeared ? 1 : 0.9)
            .opacity(appeared ? 1 : 0)
            .contentShape(shape)
            .onTapGesture {
                Haptics.tap()
                onSelect(block)
            }
            .accessibilityElement()
            .accessibilityLabel(S.Tree.blockAccessibility(block, tree: tree))
            .accessibilityAddTraits(.isButton)
    }

    private func marker(
        _ symbol: String, tint: Color, at start: Angle, end: Angle,
        inner: CGFloat, outer: CGFloat
    ) -> some View {
        let mid = Angle(degrees: (start.degrees + end.degrees) / 2)
        let radius = (inner + outer) / 2
        return Image(systemName: symbol)
            .font(.system(size: 11, weight: .bold))
            .foregroundStyle(tint)
            .offset(
                x: radius * CGFloat(cos(mid.radians)),
                y: radius * CGFloat(sin(mid.radians))
            )
            .accessibilityHidden(true)
    }

    private func markerTint(_ block: BlockSummary) -> Color {
        switch block.status {
        case .passed: return Theme.Palette.background
        case .gateReady: return hue(block)
        default: return hue(block).opacity(0.55)
        }
    }

    private func fill(for block: BlockSummary) -> some ShapeStyle {
        let colour = hue(block)
        switch block.status {
        case .passed:
            return AnyShapeStyle(
                LinearGradient(
                    colors: [colour.opacity(0.85), colour],
                    startPoint: .topLeading, endPoint: .bottomTrailing
                )
            )
        case .gateReady:
            return AnyShapeStyle(colour.opacity(0.45))
        case .inProgress:
            return AnyShapeStyle(colour.opacity(0.30))
        case .available:
            return AnyShapeStyle(colour.opacity(0.20))
        case .locked:
            // Visible, but clearly not yours yet.
            return AnyShapeStyle(colour.opacity(0.09))
        }
    }

    private func stroke(for block: BlockSummary) -> Color {
        switch block.status {
        case .passed, .gateReady: return hue(block)
        case .inProgress, .available: return hue(block).opacity(0.65)
        case .locked: return hue(block).opacity(0.25)
        }
    }

    /// Domain initial on the outer edge, so the six sectors can be told apart without
    /// tapping into them.
    private func domainLabel(_ domain: DomainView, index: Int, radius: CGFloat) -> some View {
        let mid = Angle(degrees: (Double(index) + 0.5) * sweep - 90)
        // The block-id letters rather than the domain's initial: three domain names
        // start with the same Cyrillic letter, and this matches the ids shown elsewhere.
        // System Design ids are two letters — `SC` and `SE` would collide as one.
        let code = tree.blocks(inDomain: domain.key).first.map {
            String($0.id.dropLast())
        }
        return Text(code ?? "")
            .font(.caption2.weight(.bold))
            .foregroundStyle(
                (Self.domainHues[domain.key] ?? Theme.Palette.accent).opacity(0.8)
            )
            .offset(
                x: radius * CGFloat(cos(mid.radians)),
                y: radius * CGFloat(sin(mid.radians))
            )
            .accessibilityHidden(true)
    }

    private var centre: some View {
        VStack(spacing: 2) {
            Text("\(tree.blocks.filter { $0.status == .passed }.count)")
                .font(.title3.weight(.bold).monospacedDigit())
            Text(S.Tree.ofBlocks(tree.blocks.count))
                .font(.caption2)
                .foregroundStyle(Theme.Palette.secondaryText)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(
            S.Tree.passedOfTotal(
                tree.blocks.filter { $0.status == .passed }.count, tree.blocks.count
            )
        )
    }
}
