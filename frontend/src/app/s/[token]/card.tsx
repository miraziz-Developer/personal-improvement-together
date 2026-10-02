// The picture behind a shared link, drawn by next/og (flex layout and inline styles only).
import { CATEGORY_EMOJI, headline, type Shared } from "@/lib/share";

export function ShareCard({ shared, story }: { shared: Shared; story: boolean }) {
  const { big, small } = headline(shared);
  const progress = shared.total_days ? Math.min(shared.days_completed / shared.total_days, 1) : 0;
  const scale = story ? 1.6 : 1;
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: 64 * scale,
        background: "linear-gradient(135deg, #0b0b14 0%, #1c1030 55%, #3a1424 100%)",
        color: "white",
        fontFamily: "sans-serif",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 16 * scale }}>
        <div
          style={{
            width: 64 * scale,
            height: 64 * scale,
            borderRadius: 18 * scale,
            background: "linear-gradient(135deg, #ff9a3d, #ff3d7f)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 38 * scale,
          }}
        >
          🔥
        </div>
        <div style={{ fontSize: 40 * scale, fontWeight: 800 }}>PIT</div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 * scale }}>
        <div style={{ display: "flex", fontSize: 34 * scale, color: "#c9c9d6" }}>{`@${shared.username}`}</div>
        <div style={{ display: "flex", flexDirection: story ? "column" : "row", alignItems: story ? "flex-start" : "baseline", gap: 20 * scale }}>
          <div style={{ display: "flex", fontSize: 150 * scale, fontWeight: 900, lineHeight: 1, color: "#ffb15c" }}>{big}</div>
          <div style={{ display: "flex", fontSize: 44 * scale, fontWeight: 700 }}>{small}</div>
        </div>
        <div style={{ display: "flex", fontSize: 44 * scale, fontWeight: 700, marginTop: 8 * scale }}>
          {`${CATEGORY_EMOJI[shared.category] ?? "🎯"} ${shared.title}`}
        </div>
        <div style={{ display: "flex", width: "100%", height: 18 * scale, borderRadius: 999, background: "rgba(255,255,255,0.12)", marginTop: 16 * scale }}>
          <div style={{ width: `${progress * 100}%`, height: "100%", borderRadius: 999, background: "linear-gradient(90deg, #ff9a3d, #ff3d7f)" }} />
        </div>
        <div style={{ display: "flex", fontSize: 28 * scale, color: "#c9c9d6" }}>
          {`${shared.days_completed}/${shared.total_days} kun · eng uzun streak ${shared.best_streak}`}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: story ? "column" : "row", gap: 12 * scale, justifyContent: "space-between", alignItems: story ? "flex-start" : "center", fontSize: 28 * scale, color: "#c9c9d6" }}>
        <div>Men bilan birga boshla 👇</div>
        <div style={{ fontWeight: 700, color: "white" }}>pit-uz.vercel.app</div>
      </div>
    </div>
  );
}
